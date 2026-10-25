"""
Evidence corpus manager coordinating point-in-time multi-modal evidence ingestion.
"""
from pathlib import Path
from typing import List, Dict, Tuple
from code.config import EVIDENCE_FILES_MANIFEST, DATASET_DIR
from code.utils.csv_loader import load_csv
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import DiscoveredRecord
from code.evidence.sql_parser import SqlEvidenceParser
from code.evidence.json_parser import JsonEvidenceParser
from code.evidence.log_parser import LogEvidenceParser
from code.evidence.text_parser import TextEvidenceParser
from code.evidence.pdf_extractor import PdfEvidenceParser
from code.evidence.image_analyzer import ImageEvidenceParser

class EvidenceCorpus:
    """
    Manages manifest indexing, temporal filtering at audit_at, and multi-modal parser dispatch.
    """
    def __init__(self, manifest_path: Path = EVIDENCE_FILES_MANIFEST):
        self.manifest_path = manifest_path
        self.manifest_entries = load_csv(manifest_path)
        
        # Instantiate parsers
        self.sql_parser = SqlEvidenceParser()
        self.json_parser = JsonEvidenceParser()
        self.log_parser = LogEvidenceParser()
        self.text_parser = TextEvidenceParser()
        self.pdf_parser = PdfEvidenceParser()
        self.image_parser = ImageEvidenceParser()

    def get_records_for_user(self, user: UserIdentityCluster, audit_at: str) -> List[DiscoveredRecord]:
        """
        Ingest all evidence files captured at or before audit_at for this user.
        """
        all_discovered: List[DiscoveredRecord] = []

        for entry in self.manifest_entries:
            file_id = entry["file_id"]
            rel_path = entry["file_path"]
            captured_at = entry["captured_at"]

            # Strict temporal boundary check
            if captured_at > audit_at:
                continue

            full_path = DATASET_DIR / rel_path
            ext = full_path.suffix.lower()

            try:
                if ext == ".sql":
                    records = self.sql_parser.parse(full_path, file_id, captured_at, user)
                elif ext == ".json":
                    records = self.json_parser.parse(full_path, file_id, captured_at, user)
                elif ext == ".log":
                    records = self.log_parser.parse(full_path, file_id, captured_at, user)
                elif ext == ".txt":
                    records = self.text_parser.parse(full_path, file_id, captured_at, user)
                elif ext == ".pdf":
                    records = self.pdf_parser.parse(full_path, file_id, captured_at, user)
                elif ext == ".png":
                    records = self.image_parser.parse(full_path, file_id, captured_at, user)
                else:
                    records = []

                all_discovered.extend(records)
            except Exception:
                pass

        # Deduplicate by (system_id, resource_id), keeping the most temporally recent state
        record_map: Dict[Tuple[str, str], DiscoveredRecord] = {}
        for rec in sorted(all_discovered, key=lambda x: x.captured_at):
            record_map[(rec.system_id, rec.resource_id)] = rec

        return list(record_map.values())
