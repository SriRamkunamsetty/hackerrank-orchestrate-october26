"""
Step builder and sequencer translating discovered records into deterministic, policy-compliant steps.
"""
from typing import List, Dict, Any, Tuple
from code.config import PHASE_ORDER, OPERATION_ORDER
from code.evidence.base_parser import DiscoveredRecord
from code.policy.deletion_rules import PolicyEngine

class StepBuilder:
    """
    Constructs and sequences FINDING, REMEDIATION, and VERIFICATION steps
    strictly adhering to the HackerRank operations table and tie-breaking contracts.
    """
    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine

    def build_steps(self, records: List[DiscoveredRecord]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Returns (deletion_status, steps_list).
        deletion_status is either 'COMPLETE' or 'INCOMPLETE'.
        """
        if not records:
            # Default empty verification
            return "COMPLETE", []

        violations = [r for r in records if r.is_violation]

        if not violations:
            # Case is COMPLETE: only verification steps proving compliant state
            raw_steps = []
            for r in records:
                rule = self.policy_engine.get_rule_for_category(r.category)
                req_action = rule.required_action if rule else "DELETE"
                op, state = self.policy_engine.get_verification_operation(r.category, req_action)

                raw_steps.append({
                    "phase": "VERIFICATION",
                    "system_id": r.system_id,
                    "resource_id": r.resource_id,
                    "operation": op,
                    "state": state,
                    "evidence_id": r.evidence_id,
                })

            sorted_steps = self._sort_steps(raw_steps)
            return "COMPLETE", sorted_steps

        # Case is INCOMPLETE: findings + remediation + verification
        raw_steps = []

        # 1. Findings (citing participant-visible evidence_id)
        for r in violations:
            rule = self.policy_engine.get_rule_for_category(r.category)
            req_action = rule.required_action if rule else "DELETE"
            op, state = self.policy_engine.get_finding_operation(r.category, req_action)

            raw_steps.append({
                "phase": "FINDING",
                "system_id": r.system_id,
                "resource_id": r.resource_id,
                "operation": op,
                "state": state,
                "evidence_id": r.evidence_id,
            })

        # 2. Remediation (proposed future actions, evidence_id = "")
        for r in violations:
            rule = self.policy_engine.get_rule_for_category(r.category)
            req_action = rule.required_action if rule else "DELETE"
            op, state = self.policy_engine.get_remediation_operation(r.category, req_action)

            raw_steps.append({
                "phase": "REMEDIATION",
                "system_id": r.system_id,
                "resource_id": r.resource_id,
                "operation": op,
                "state": state,
                "evidence_id": "",
            })

        # 3. Post-remediation verification (all records must reach required state, evidence_id = "")
        for r in records:
            rule = self.policy_engine.get_rule_for_category(r.category)
            req_action = rule.required_action if rule else "DELETE"
            op, state = self.policy_engine.get_verification_operation(r.category, req_action)

            raw_steps.append({
                "phase": "VERIFICATION",
                "system_id": r.system_id,
                "resource_id": r.resource_id,
                "operation": op,
                "state": state,
                "evidence_id": "",
            })

        sorted_steps = self._sort_steps(raw_steps)
        return "INCOMPLETE", sorted_steps

    def _sort_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort order:
        1. Phase: FINDING -> REMEDIATION -> VERIFICATION
        2. Operation: defined by OPERATION_ORDER
        3. system_id: ascending
        4. resource_id: ascending
        """
        def sort_key(s: Dict[str, Any]):
            phase_rank = PHASE_ORDER.get(s["phase"], 99)
            op_rank = OPERATION_ORDER.get(s["operation"], 99)
            return (phase_rank, op_rank, s["system_id"], s["resource_id"])

        sorted_list = sorted(steps, key=sort_key)

        # Assign 1-indexed consecutive step numbers
        final_steps = []
        for i, s in enumerate(sorted_list, start=1):
            s_copy = dict(s)
            s_copy["step_no"] = i
            # Reorder dict keys for clean serialization
            ordered_step = {
                "step_no": s_copy["step_no"],
                "phase": s_copy["phase"],
                "system_id": s_copy["system_id"],
                "resource_id": s_copy["resource_id"],
                "operation": s_copy["operation"],
                "state": s_copy["state"],
                "evidence_id": s_copy["evidence_id"],
            }
            final_steps.append(ordered_step)

        return final_steps
