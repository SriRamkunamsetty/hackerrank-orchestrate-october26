"""
Policy rules engine mapping data categories to required actions and operation types.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from code.config import DELETION_RULES_FILE
from code.utils.csv_loader import load_csv

@dataclass
class DeletionRule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str  # DELETE, REDACT, ANONYMIZE, RETAIN

class PolicyEngine:
    """
    Loads deletion_rules.csv and translates resource categories into operations and states.
    """
    def __init__(self, rules_path: Path = DELETION_RULES_FILE):
        self.rules_path = rules_path
        self.rules: Dict[str, DeletionRule] = {}
        self._load_rules()

    def _load_rules(self):
        rows = load_csv(self.rules_path)
        for r in rows:
            rule = DeletionRule(
                rule_id=r["rule_id"].strip(),
                data_category=r["data_category"].strip(),
                condition=r["condition"].strip(),
                required_action=r["required_action"].strip().upper(),
            )
            self.rules[rule.data_category] = rule

    def get_rule_for_category(self, category: str) -> Optional[DeletionRule]:
        return self.rules.get(category.strip().upper())

    @staticmethod
    def get_finding_operation(category: str, required_action: str) -> Tuple_Op_State:
        cat_upper = category.upper()
        if "DATA_FLOW" in cat_upper or "CONNECTOR" in cat_upper or "INTEGRATION" in cat_upper:
            return ("REPORT_ACTIVE_DATA_FLOW", "ACTIVE")
        if "BACKUP" in cat_upper or "RESTORE" in cat_upper:
            return ("REPORT_RESTORE_RISK", "ACTIVE")
        if required_action in ("REDACT", "ANONYMIZE"):
            return ("REPORT_EXPOSED_PII", "PRESENT")
        return ("REPORT_REMAINING_RECORD", "PRESENT")

    @staticmethod
    def get_remediation_operation(category: str, required_action: str) -> Tuple_Op_State:
        cat_upper = category.upper()
        if "DATA_FLOW" in cat_upper or "CONNECTOR" in cat_upper or "INTEGRATION" in cat_upper:
            return ("DISABLE_DATA_FLOW", "DISABLED")
        if "BACKUP" in cat_upper or "RESTORE" in cat_upper:
            return ("BLOCK_RESTORE", "BLOCKED")
        if required_action == "REDACT":
            return ("REDACT_RECORD", "REDACTED")
        if required_action == "ANONYMIZE":
            return ("ANONYMIZE_RECORD", "ANONYMIZED")
        return ("DELETE_RECORD", "ABSENT")

    @staticmethod
    def get_verification_operation(category: str, required_action: str) -> Tuple_Op_State:
        cat_upper = category.upper()
        if "DATA_FLOW" in cat_upper or "CONNECTOR" in cat_upper or "INTEGRATION" in cat_upper:
            return ("VERIFY_DATA_FLOW_DISABLED", "DISABLED")
        if "BACKUP" in cat_upper or "RESTORE" in cat_upper:
            return ("VERIFY_RESTORE_BLOCKED", "BLOCKED")
        if required_action == "RETAIN":
            return ("VERIFY_RECORD_PRESENT", "PRESENT")
        if required_action == "REDACT":
            return ("VERIFY_RECORD_REDACTED", "REDACTED")
        if required_action == "ANONYMIZE":
            return ("VERIFY_RECORD_ANONYMIZED", "ANONYMIZED")
        return ("VERIFY_RECORD_ABSENT", "ABSENT")

Tuple_Op_State = tuple[str, str]
