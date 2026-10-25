"""
Parser for structured pipe-delimited shift handover plain-text files.
"""
from pathlib import Path
from typing import List
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

STATUS_STATE_MAP = {
    "NOT_FOUND": "ABSENT",
    "FOUND": "PRESENT",
    "IDENTIFIABLE": "PRESENT",
    "ANONYMIZED": "ANONYMIZED",
    "ACTIVE": "ACTIVE",
    "DISABLED": "DISABLED",
    "BLOCKED": "BLOCKED",
    "REDACTED": "REDACTED",
}

class TextEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        if not file_path.exists():
            return records

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("-") or "|" not in line:
                    continue

                parts = [p.strip() for p in line.lstrip("-").split("|")]
                if len(parts) < 6:
                    continue

                ts, system_id, resource_id, category, status_raw, identifier = parts[:6]

                # Match user against identifier or user_id
                if not user.matches_identifier(identifier) and identifier.lower() != "no direct identifier":
                    continue

                state = STATUS_STATE_MAP.get(status_raw.upper(), status_raw.upper())

                # Determine if violation based on category and state
                is_violation = False
                cat_upper = category.upper()

                if cat_upper in ("DATA_FLOW", "INTEGRATION_CONNECTOR") and state == "ACTIVE":
                    is_violation = True
                elif "BACKUP" in cat_upper and state == "ACTIVE":
                    is_violation = True
                elif cat_upper in ("USER_PROFILE", "SEARCH_INDEX_ENTRY", "USER_EXPORT", "MARKETING_PROFILE") and state == "PRESENT":
                    is_violation = True
                elif cat_upper in ("ANALYTICS_PROFILE", "SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE") and status_raw.upper() in ("IDENTIFIABLE", "FOUND", "PRESENT"):
                    is_violation = True

                records.append(DiscoveredRecord(
                    system_id=system_id,
                    resource_id=resource_id,
                    category=category,
                    state=state,
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=is_violation,
                    details=f"Handover check: {status_raw} for {identifier}"
                ))

        return records
