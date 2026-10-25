"""
Base models and abstract parser definition for evidence ingestion.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from code.agent.identity_resolver import UserIdentityCluster

@dataclass
class DiscoveredRecord:
    system_id: str
    resource_id: str
    category: str
    state: str  # PRESENT, ABSENT, ACTIVE, DISABLED, BLOCKED, ANONYMIZED, REDACTED
    evidence_id: str
    captured_at: str
    is_violation: bool
    details: str = ""

class BaseEvidenceParser(ABC):
    """
    Abstract parser interface for extracting customer records from evidence files.
    """
    @abstractmethod
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        pass
