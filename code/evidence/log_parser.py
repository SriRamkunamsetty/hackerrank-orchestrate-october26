"""
Log evidence parser for structured observability and readback logs.
Includes two-pass distributed trace correlation to link lookup_key/subject_key to resource_id.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Set
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

class LogEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        if not file_path.exists():
            return records

        parsed_lines: List[Dict[str, str]] = []
        matching_trace_ids: Set[str] = set()

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                kv: Dict[str, str] = {}
                if "{" in line and line.endswith("}"):
                    json_str = line[line.find("{"):]
                    try:
                        parsed = json.loads(json_str)
                        if isinstance(parsed, dict):
                            for k, v in parsed.items():
                                kv[k] = str(v).strip() if v is not None else "null"
                    except Exception:
                        pass

                if not kv:
                    kv_matches = re.findall(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))', line)
                    if not kv_matches:
                        continue
                    for m in kv_matches:
                        k = m[0]
                        v = m[1] or m[2] or m[3] or ""
                        kv[k] = v.strip()

                parsed_lines.append(kv)

                # Check if this line directly mentions user
                trace_id = kv.get("trace_id")
                direct_match = any(val and val != "null" and user.matches_identifier(val) for val in kv.values())
                if direct_match and trace_id:
                    matching_trace_ids.add(trace_id)

        # Pass 2: Process events correlated by trace_id or direct identifier match
        for kv in parsed_lines:
            trace_id = kv.get("trace_id")
            direct_match = any(val and val != "null" and user.matches_identifier(val) for val in kv.values())
            is_relevant = direct_match or (trace_id and trace_id in matching_trace_ids)

            if not is_relevant:
                continue

            service = (kv.get("service") or kv.get("source_system") or "account_service").lower()
            res_id = kv.get("resource_id") or kv.get("target_resource")
            event = kv.get("event", "")

            # If no resource_id on this line, skip record creation unless it's an actionable status
            if not res_id:
                continue

            if "account" in service:
                status_code = kv.get("http_status") or kv.get("status_code")
                rows = kv.get("rows")
                if status_code == "404" or rows == "0":
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
                elif status_code == "200" or rows == "1":
                    records.append(DiscoveredRecord(
                        system_id="account_service",
                        resource_id=res_id,
                        category="USER_PROFILE",
                        state="PRESENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=True,
                        details="Surviving account profile found in readback log"
                    ))

            elif "search" in service:
                result = kv.get("result", "")
                hits = kv.get("total_hits", "0")
                if result == "hit" or (hits.isdigit() and int(hits) > 0):
                    records.append(DiscoveredRecord(
                        system_id="search_service",
                        resource_id=res_id,
                        category="SEARCH_INDEX_ENTRY",
                        state="PRESENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=True,
                        details="Surviving search index hit found"
                    ))
                else:
                    records.append(DiscoveredRecord(
                        system_id="search_service",
                        resource_id=res_id,
                        category="SEARCH_INDEX_ENTRY",
                        state="ABSENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=False,
                        details="Search index query returned 0 hits"
                    ))

            elif "integration" in service or "connector" in service or "bridge" in service:
                enabled = kv.get("enabled", "").lower() == "true"
                records.append(DiscoveredRecord(
                    system_id="integration_service",
                    resource_id=res_id,
                    category="INTEGRATION_CONNECTOR",
                    state="ACTIVE" if enabled else "DISABLED",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=enabled,
                    details=f"Connector {res_id} enabled={enabled}"
                ))

            elif "backup" in service or "restore" in service:
                restore_allowed = kv.get("restore_allowed", "").lower() == "true"
                deletion_block = kv.get("deletion_block", "").lower()
                eligible = kv.get("eligible", "").lower() == "true"

                is_risk = restore_allowed or (eligible and deletion_block == "false")
                records.append(DiscoveredRecord(
                    system_id="backup_service",
                    resource_id=res_id,
                    category="BACKUP_ARCHIVE",
                    state="ACTIVE" if is_risk else "BLOCKED",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=is_risk,
                    details=f"Backup archive {res_id} restore risk={is_risk}"
                ))

            elif "security" in service or "sentinel" in service or "audit" in service:
                records.append(DiscoveredRecord(
                    system_id="security_service",
                    resource_id=res_id,
                    category="SECURITY_AUDIT_LOG",
                    state="PRESENT",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=False,
                    details=f"Security audit record {res_id} retained"
                ))

            elif "support" in service:
                marker_found = kv.get("marker_found", "").lower()
                rows = kv.get("rows", "")
                if marker_found == "false" or (rows == "1" and "replica" in service):
                    records.append(DiscoveredRecord(
                        system_id="support_platform",
                        resource_id=res_id,
                        category="SUPPORT_MESSAGE",
                        state="PRESENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=True,
                        details="Support replica record found without deletion marker"
                    ))
                else:
                    has_pii = any(kv.get(k) and kv[k] != "null" for k in ("requester_email", "requester_phone", "requester_name"))
                    records.append(DiscoveredRecord(
                        system_id="support_platform",
                        resource_id=res_id,
                        category="SUPPORT_MESSAGE",
                        state="PRESENT" if has_pii else "REDACTED",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=has_pii,
                        details=f"Support ticket {res_id} PII state"
                    ))

            elif "analytics" in service:
                rows = kv.get("rows", "0")
                if rows == "1" or kv.get("email_opt_in") == "true":
                    records.append(DiscoveredRecord(
                        system_id="analytics_platform",
                        resource_id=res_id,
                        category="ANALYTICS_PROFILE",
                        state="PRESENT",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=True,
                        details="Surviving analytics profile record found"
                    ))
                else:
                    has_pii = any(kv.get(k) and kv[k] != "null" for k in ("email", "phone", "email_hash", "customer_reference"))
                    records.append(DiscoveredRecord(
                        system_id="analytics_platform",
                        resource_id=res_id,
                        category="ANALYTICS_PROFILE",
                        state="PRESENT" if has_pii else "ANONYMIZED",
                        evidence_id=evidence_id,
                        captured_at=captured_at,
                        is_violation=has_pii,
                        details=f"Analytics profile {res_id} anonymization state"
                    ))

        return records
