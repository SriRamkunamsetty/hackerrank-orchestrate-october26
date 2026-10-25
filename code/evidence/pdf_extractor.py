"""
Zero-dependency PDF text extractor handling both FlateDecode and Adobe ASCII85 streams.
"""
import base64
import zlib
import re
from pathlib import Path
from typing import List
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

class PdfEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        if not file_path.exists():
            return records

        with open(file_path, "rb") as f:
            content = f.read()

        parts = content.split(b"stream")
        extracted_text_lines = []

        for i in range(1, len(parts)):
            seg = parts[i]
            if b"end" not in seg:
                continue
            data = seg.split(b"end")[0].strip()

            decomp = None
            try:
                decomp = zlib.decompress(data)
            except Exception:
                pass

            if not decomp:
                try:
                    a85 = data if data.endswith(b"~>") else data + b"~>"
                    decomp = zlib.decompress(base64.a85decode(a85, adobe=True))
                except Exception:
                    pass

            if decomp and b"BT" in decomp:
                strings = re.findall(r"\((.*?)\)\s*Tj", decomp.decode("latin1", errors="ignore"))
                extracted_text_lines.extend(strings)

        full_doc_text = " ".join(extracted_text_lines)

        # Check if user matches document content
        matches_user = (
            user.user_id in full_doc_text or
            any(e.lower() in full_doc_text.lower() for e in user.emails) or
            any(n.lower() in full_doc_text.lower() for n in user.names)
        )

        if matches_user:
            # Identify document resource category and system
            file_name = file_path.stem.lower()
            if "delivery_correction" in file_name or "support" in file_name:
                system_id = "support_platform"
                res_match = re.search(r"support_\d+", full_doc_text)
                resource_id = res_match.group(0) if res_match else "support_attachment_001"
                category = "SUPPORT_ATTACHMENT"
                records.append(DiscoveredRecord(
                    system_id=system_id,
                    resource_id=resource_id,
                    category=category,
                    state="PRESENT",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=True,
                    details=f"Identity document found in support attachment {resource_id}"
                ))
            elif "legal_retention" in file_name:
                system_id = "security_service"
                res_match = re.search(r"legal_hold_\d+|audit_record_\d+", full_doc_text)
                resource_id = res_match.group(0) if res_match else f"legal_record_{user.user_id}"
                category = "LEGAL_HOLD_RECORD"
                records.append(DiscoveredRecord(
                    system_id=system_id,
                    resource_id=resource_id,
                    category=category,
                    state="PRESENT",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=False,
                    details=f"Required legal hold record {resource_id}"
                ))
            elif "security_retention" in file_name:
                system_id = "security_service"
                res_match = re.search(r"audit_record_\d+", full_doc_text)
                resource_id = res_match.group(0) if res_match else f"audit_record_{user.user_id}"
                category = "SECURITY_AUDIT_LOG"
                records.append(DiscoveredRecord(
                    system_id=system_id,
                    resource_id=resource_id,
                    category=category,
                    state="PRESENT",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=False,
                    details=f"Required security audit record {resource_id}"
                ))
            elif "account_history" in file_name:
                system_id = "account_service"
                res_match = re.search(r"account_\d+", full_doc_text)
                resource_id = res_match.group(0) if res_match else f"account_{user.user_id}"
                category = "USER_PROFILE"
                records.append(DiscoveredRecord(
                    system_id=system_id,
                    resource_id=resource_id,
                    category=category,
                    state="PRESENT",
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=True,
                    details=f"Account profile document found {resource_id}"
                ))

        return records
