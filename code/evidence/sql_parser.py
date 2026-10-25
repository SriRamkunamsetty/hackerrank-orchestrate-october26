"""
SQLite in-memory executor for inspecting SQL point-in-time snapshots and replication drift.
Handles structured table schemas as well as document store tables with record_json blobs.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

TABLE_SYSTEM_MAP = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_profiles_primary": ("account_service", "USER_PROFILE"),
    "customer_profiles_failover_replica": ("account_service", "USER_PROFILE"),
    "customer_data_inventory": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "search_documents_primary": ("search_service", "SEARCH_INDEX_ENTRY"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "customer_analytics_profiles": ("analytics_platform", "ANALYTICS_PROFILE"),
    "connector_subscriptions": ("integration_service", "INTEGRATION_CONNECTOR"),
    "backup_restore_entries": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_records": ("security_service", "SECURITY_AUDIT_LOG"),
}

COLLECTION_MAP = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_reports": ("analytics_platform", "ANALYTICS_PROFILE"),
    "security_audit_events": ("security_service", "SECURITY_AUDIT_LOG"),
    "support_cases": ("support_platform", "SUPPORT_MESSAGE"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "connector_configurations": ("integration_service", "INTEGRATION_CONNECTOR"),
    "backup_restore_policies": ("backup_service", "BACKUP_ARCHIVE"),
    "deleted_customer_references": ("identity_service", "ACCOUNT_TOMBSTONE"),
}

class SqlEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        if not file_path.exists():
            return records

        with open(file_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(sql_content)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [c[1] for c in cur.fetchall()]

                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()

                # Check if this is a generic document table with record_json
                if "record_json" in cols:
                    json_idx = cols.index("record_json")
                    sys_idx = cols.index("origin_system") if "origin_system" in cols else None
                    coll_idx = cols.index("collection_name") if "collection_name" in cols else None
                    res_idx = cols.index("resource_id") if "resource_id" in cols else None

                    for r in rows:
                        json_str = r[json_idx]
                        if not json_str:
                            continue
                        try:
                            item = json.loads(json_str) if isinstance(json_str, str) else json_str
                        except Exception:
                            continue

                        # Check if item matches user
                        matched = False
                        def check_match(val):
                            if isinstance(val, dict):
                                return any(check_match(v) for v in val.values())
                            elif isinstance(val, (list, set)):
                                return any(check_match(v) for v in val)
                            elif val:
                                return user.matches_identifier(str(val))
                            return False

                        if check_match(item):
                            matched = True

                        if not matched and res_idx is not None and r[res_idx]:
                            if user.matches_identifier(str(r[res_idx])):
                                matched = True

                        if matched:
                            resource_id = str(r[res_idx]) if res_idx is not None and r[res_idx] else item.get("resource_id", "")
                            origin_sys = str(r[sys_idx]) if sys_idx is not None and r[sys_idx] else ""
                            coll_name = str(r[coll_idx]) if coll_idx is not None and r[coll_idx] else ""

                            sys_id, cat = COLLECTION_MAP.get(coll_name, (origin_sys or "account_service", "USER_PROFILE"))
                            if origin_sys:
                                sys_id = origin_sys

                            is_violation = False
                            if cat in ("USER_PROFILE", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "MARKETING_PROFILE"):
                                # If present in replica, it's a surviving copy
                                status = str(item.get("account_status") or item.get("status") or "ACTIVE").upper()
                                is_violation = (status != "DELETED")
                                state = "PRESENT" if is_violation else "ABSENT"
                            elif cat == "SECURITY_AUDIT_LOG":
                                is_violation = False
                                state = "PRESENT"
                            elif cat == "BACKUP_ARCHIVE":
                                is_violation = (item.get("restore_allowed") in (1, True, "true"))
                                state = "ACTIVE" if is_violation else "BLOCKED"
                            elif cat in ("INTEGRATION_CONNECTOR", "DATA_FLOW"):
                                is_violation = (item.get("enabled") in (1, True, "true"))
                                state = "ACTIVE" if is_violation else "DISABLED"
                            elif cat in ("ANALYTICS_PROFILE", "SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"):
                                has_pii = any(
                                    item.get(field) and str(item[field]).strip()
                                    for field in ("email", "phone", "full_name", "customer_name", "email_hash", "name")
                                )
                                is_violation = has_pii
                                state = "PRESENT" if is_violation else ("ANONYMIZED" if cat == "ANALYTICS_PROFILE" else "REDACTED")
                            else:
                                state = "PRESENT"

                            records.append(DiscoveredRecord(
                                system_id=sys_id,
                                resource_id=resource_id,
                                category=cat,
                                state=state,
                                evidence_id=evidence_id,
                                captured_at=captured_at,
                                is_violation=is_violation,
                                details=f"SQL table {table} JSON document: {coll_name}"
                            ))

                else:
                    # Regular relational table
                    system_id, category = TABLE_SYSTEM_MAP.get(table, ("account_service", "USER_PROFILE"))
                    for r in rows:
                        row_dict = dict(zip(cols, r))
                        matched = any(val and user.matches_identifier(str(val)) for val in row_dict.values())

                        if matched:
                            resource_id = row_dict.get("resource_id") or row_dict.get("id") or f"{table}_{user.user_id}"
                            status = str(row_dict.get("account_status") or row_dict.get("status") or "ACTIVE").upper()

                            is_violation = False
                            if category in ("USER_PROFILE", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "MARKETING_PROFILE"):
                                is_violation = (status != "DELETED")
                                state = "PRESENT" if is_violation else "ABSENT"
                            elif category == "SECURITY_AUDIT_LOG":
                                is_violation = False
                                state = "PRESENT"
                            elif category == "BACKUP_ARCHIVE":
                                is_violation = (status == "ACTIVE" or row_dict.get("restore_allowed") in (1, True, "true"))
                                state = "ACTIVE" if is_violation else "BLOCKED"
                            elif category == "INTEGRATION_CONNECTOR":
                                is_violation = (status == "ACTIVE" or row_dict.get("enabled") in (1, True, "true"))
                                state = "ACTIVE" if is_violation else "DISABLED"
                            elif category in ("ANALYTICS_PROFILE", "SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE"):
                                has_direct_pii = any(
                                    row_dict.get(field) and str(row_dict[field]).strip()
                                    for field in ("email", "phone", "full_name", "customer_name", "email_hash")
                                )
                                is_violation = has_direct_pii
                                state = "PRESENT" if is_violation else ("ANONYMIZED" if category == "ANALYTICS_PROFILE" else "REDACTED")
                            else:
                                state = "PRESENT"

                            records.append(DiscoveredRecord(
                                system_id=system_id,
                                resource_id=resource_id,
                                category=category,
                                state=state,
                                evidence_id=evidence_id,
                                captured_at=captured_at,
                                is_violation=is_violation,
                                details=f"SQL table {table}: status={status}"
                            ))

        except Exception:
            pass
        finally:
            conn.close()

        return records
