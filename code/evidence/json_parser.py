"""
JSON evidence parser for customer snapshot bundles, service resource exports, and stand-alone record collections.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

class JsonEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        if not file_path.exists():
            return records

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                return records

        def check_match(val):
            if isinstance(val, dict):
                return any(check_match(v) for v in val.values())
            elif isinstance(val, (list, set)):
                return any(check_match(v) for v in val)
            elif val:
                return user.matches_identifier(str(val))
            return False

        # 1. Handle service_resource_export format
        if "service_exports" in data:
            exports = data["service_exports"]
            
            # account_service
            if "account_service" in exports:
                lookups = exports["account_service"].get("profile_lookups", [])
                for item in lookups:
                    prof = item.get("profile")
                    res_id = item.get("resource_id") or f"account_{user.user_id}"
                    status_code = item.get("status_code", 404)

                    matched = False
                    if prof and check_match(prof):
                        matched = True
                    elif user.matches_identifier(res_id):
                        matched = True

                    if matched:
                        if status_code == 200 and prof is not None:
                            records.append(DiscoveredRecord(
                                system_id="account_service",
                                resource_id=res_id,
                                category="USER_PROFILE",
                                state="PRESENT",
                                evidence_id=evidence_id,
                                captured_at=captured_at,
                                is_violation=True,
                                details="Active account profile found in service export"
                            ))
                        elif status_code == 404 or prof is None:
                            records.append(DiscoveredRecord(
                                system_id="account_service",
                                resource_id=res_id,
                                category="USER_PROFILE",
                                state="ABSENT",
                                evidence_id=evidence_id,
                                captured_at=captured_at,
                                is_violation=False,
                                details="Account profile absent (HTTP 404)"
                            ))

            # analytics_platform
            if "analytics_platform" in exports:
                profiles = exports["analytics_platform"].get("profiles", [])
                for p in profiles:
                    res_id = p.get("resource_id")
                    matched = check_match(p)
                    if matched or user.matches_identifier(res_id):
                        has_pii = any(p.get(k) and str(p[k]).strip() for k in ("email", "phone", "email_hash", "customer_reference"))
                        records.append(DiscoveredRecord(
                            system_id="analytics_platform",
                            resource_id=res_id,
                            category="ANALYTICS_PROFILE",
                            state="PRESENT" if has_pii else "ANONYMIZED",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=has_pii,
                            details="Analytics profile state"
                        ))

            # integration_service
            if "integration_service" in exports:
                connectors = exports["integration_service"].get("connectors", [])
                for c in connectors:
                    res_id = c.get("resource_id")
                    if check_match(c):
                        is_active = c.get("enabled", False) is True
                        records.append(DiscoveredRecord(
                            system_id="integration_service",
                            resource_id=res_id,
                            category="INTEGRATION_CONNECTOR",
                            state="ACTIVE" if is_active else "DISABLED",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=is_active,
                            details="Integration connector state"
                        ))

            # backup_service
            if "backup_service" in exports:
                archives = exports["backup_service"].get("archives", []) or exports["backup_service"].get("restore_entries", [])
                for a in archives:
                    res_id = a.get("resource_id")
                    if check_match(a):
                        restore_allowed = a.get("restore_allowed", False) is True
                        records.append(DiscoveredRecord(
                            system_id="backup_service",
                            resource_id=res_id,
                            category="BACKUP_ARCHIVE",
                            state="ACTIVE" if restore_allowed else "BLOCKED",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=restore_allowed,
                            details="Backup restore status"
                        ))

            # security_service
            if "security_service" in exports:
                audit_records = exports["security_service"].get("audit_records", [])
                for ar in audit_records:
                    res_id = ar.get("resource_id")
                    if check_match(ar):
                        records.append(DiscoveredRecord(
                            system_id="security_service",
                            resource_id=res_id,
                            category="SECURITY_AUDIT_LOG",
                            state="PRESENT",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=False,
                            details="Retained security audit log"
                        ))

            # support_platform
            if "support_platform" in exports:
                tickets = exports["support_platform"].get("tickets", [])
                for t in tickets:
                    res_id = t.get("resource_id")
                    if check_match(t):
                        has_pii = any(t.get(k) and str(t[k]).strip() for k in ("requester_email", "requester_phone", "requester_name"))
                        records.append(DiscoveredRecord(
                            system_id="support_platform",
                            resource_id=res_id,
                            category="SUPPORT_MESSAGE",
                            state="PRESENT" if has_pii else "REDACTED",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=has_pii,
                            details="Support ticket conversation"
                        ))

            # export_service
            if "export_service" in exports:
                jobs = exports["export_service"].get("exports", [])
                for j in jobs:
                    res_id = j.get("resource_id")
                    if check_match(j):
                        status = str(j.get("status", "READY")).upper()
                        is_viol = (status != "DELETED")
                        records.append(DiscoveredRecord(
                            system_id="export_service",
                            resource_id=res_id,
                            category="USER_EXPORT",
                            state="PRESENT" if is_viol else "ABSENT",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=is_viol,
                            details="User export archive"
                        ))

            # search_service
            if "search_service" in exports:
                entries = exports["search_service"].get("index_entries", []) or exports["search_service"].get("index_queries", [])
                for s in entries:
                    res_id = s.get("resource_id")
                    if check_match(s):
                        records.append(DiscoveredRecord(
                            system_id="search_service",
                            resource_id=res_id,
                            category="SEARCH_INDEX_ENTRY",
                            state="PRESENT",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=True,
                            details="Search directory index entry"
                        ))

        # 2. Handle customer_data_snapshot_bundle format
        if "snapshots" in data:
            snapshots = data["snapshots"]
            for s in snapshots:
                data_store = s.get("data_store", "")
                collection = s.get("collection", "")
                items = s.get("records", [])

                for item in items:
                    if not check_match(item):
                        continue

                    res_id = item.get("resource_id") or f"{collection}_{user.user_id}"

                    if "deleted" in collection or "tombstone" in collection or data_store == "identity_service":
                        has_pii = any(item.get(k) and str(item[k]).strip() for k in ("name", "email", "phone", "email_hash"))
                        records.append(DiscoveredRecord(
                            system_id="identity_service",
                            resource_id=res_id,
                            category="ACCOUNT_TOMBSTONE",
                            state="PRESENT" if has_pii else "REDACTED",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=has_pii,
                            details="Account tombstone in identity service"
                        ))
                    elif "security" in collection or data_store == "security_service":
                        records.append(DiscoveredRecord(
                            system_id="security_service",
                            resource_id=res_id,
                            category="SECURITY_AUDIT_LOG",
                            state="PRESENT",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=False,
                            details="Security audit event"
                        ))
                    elif "profile" in collection or data_store == "account_service":
                        status = str(item.get("account_status") or item.get("status") or "ACTIVE").upper()
                        is_viol = (status != "DELETED")
                        records.append(DiscoveredRecord(
                            system_id="account_service",
                            resource_id=res_id,
                            category="USER_PROFILE",
                            state="PRESENT" if is_viol else "ABSENT",
                            evidence_id=evidence_id,
                            captured_at=captured_at,
                            is_violation=is_viol,
                            details="Account profile snapshot"
                        ))

        # 3. Handle stand-alone top-level records array (e.g. customer_export_jobs, connector_configurations)
        if "records" in data and isinstance(data["records"], list):
            collection = data.get("collection", "") or file_path.stem
            for item in data["records"]:
                if not check_match(item):
                    continue

                res_id = item.get("resource_id") or f"{collection}_{user.user_id}"

                if "export" in collection:
                    is_avail = item.get("download_available", True) is True
                    records.append(DiscoveredRecord(
                        system_id="export_service",
                        resource_id=res_id,
                        category="USER_EXPORT",
                        state="PRESENT" if is_avail else "ABSENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=is_avail,
                        details="User export job"
                    ))
                elif "connector" in collection or "data_flow" in collection:
                    enabled = item.get("enabled", True) is True
                    records.append(DiscoveredRecord(
                        system_id="integration_service",
                        resource_id=res_id,
                        category="INTEGRATION_CONNECTOR",
                        state="ACTIVE" if enabled else "DISABLED",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=enabled,
                        details="Connector configuration"
                    ))
                elif "analytics" in collection:
                    has_pii = any(item.get(k) and str(item[k]).strip() for k in ("email", "phone", "email_hash", "customer_reference"))
                    records.append(DiscoveredRecord(
                        system_id="analytics_platform",
                        resource_id=res_id,
                        category="ANALYTICS_PROFILE",
                        state="PRESENT" if has_pii else "ANONYMIZED",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=has_pii,
                        details="Analytics report record"
                    ))
                elif "security" in collection or "audit" in collection:
                    records.append(DiscoveredRecord(
                        system_id="security_service",
                        resource_id=res_id,
                        category="SECURITY_AUDIT_LOG",
                        state="PRESENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=False,
                        details="Security audit record"
                    ))

        return records
