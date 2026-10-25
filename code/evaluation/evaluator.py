"""
Comprehensive evaluation framework for Ghost Data Still Exists.
Computes case-level deletion-status accuracy, step-level precision/recall/F1,
field-level accuracy, and sequence accuracy.
"""
import csv
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

class DeletionAuditEvaluator:
    def __init__(self, ground_truth_path: Path):
        self.ground_truth_path = ground_truth_path
        self.ground_truth: Dict[str, Dict[str, Any]] = {}
        self._load_ground_truth()

    def _load_ground_truth(self):
        with open(self.ground_truth_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row["case_id"].strip()
                status = row["deletion_status"].strip()
                try:
                    steps = json.loads(row["steps_json"])
                except Exception:
                    steps = []
                self.ground_truth[cid] = {
                    "deletion_status": status,
                    "steps": steps,
                    "steps_raw": row["steps_json"]
                }

    def evaluate_predictions(self, predictions_path: Path) -> Dict[str, Any]:
        """
        Evaluate predictions against ground truth.
        """
        with open(predictions_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            pred_rows = list(reader)

        total_cases = 0
        status_matches = 0
        sequence_matches = 0

        total_gt_steps = 0
        total_pred_steps = 0
        matched_steps = 0

        # Field-level matches across matched steps
        field_matches = {
            "phase": 0,
            "operation": 0,
            "system_id": 0,
            "resource_id": 0,
            "state": 0,
            "evidence_id": 0
        }

        for row in pred_rows:
            cid = row["case_id"].strip()
            if cid not in self.ground_truth:
                continue

            total_cases += 1
            gt = self.ground_truth[cid]
            gt_status = gt["deletion_status"]
            gt_steps = gt["steps"]

            pred_status = row["deletion_status"].strip()
            try:
                pred_steps = json.loads(row["steps_json"])
            except Exception:
                pred_steps = []

            # 1. Case-level status
            if pred_status == gt_status:
                status_matches += 1

            # 2. Sequence accuracy (exact match of full ordered array)
            if pred_steps == gt_steps:
                sequence_matches += 1

            total_gt_steps += len(gt_steps)
            total_pred_steps += len(pred_steps)

            # 3. Step-level alignment (by phase, system_id, resource_id, operation)
            gt_step_tuples = [
                (s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"))
                for s in gt_steps
            ]
            pred_step_tuples = [
                (s.get("phase"), s.get("system_id"), s.get("resource_id"), s.get("operation"))
                for s in pred_steps
            ]

            # Greedy step matching
            used_pred = set()
            for g_idx, g_step in enumerate(gt_steps):
                g_tup = gt_step_tuples[g_idx]
                best_p_idx = None
                for p_idx, p_step in enumerate(pred_steps):
                    if p_idx in used_pred:
                        continue
                    if pred_step_tuples[p_idx] == g_tup:
                        best_p_idx = p_idx
                        break

                if best_p_idx is not None:
                    matched_steps += 1
                    used_pred.add(best_p_idx)
                    p_step = pred_steps[best_p_idx]

                    # Check fields
                    for field in field_matches.keys():
                        if p_step.get(field) == g_step.get(field):
                            field_matches[field] += 1

        step_precision = matched_steps / total_pred_steps if total_pred_steps > 0 else 0.0
        step_recall = matched_steps / total_gt_steps if total_gt_steps > 0 else 0.0
        step_f1 = (2 * step_precision * step_recall / (step_precision + step_recall)) if (step_precision + step_recall) > 0 else 0.0

        field_acc = {
            f: (field_matches[f] / matched_steps if matched_steps > 0 else 0.0)
            for f in field_matches
        }

        return {
            "total_cases": total_cases,
            "status_accuracy": status_matches / total_cases if total_cases > 0 else 0.0,
            "status_matches": status_matches,
            "sequence_accuracy": sequence_matches / total_cases if total_cases > 0 else 0.0,
            "sequence_matches": sequence_matches,
            "step_precision": step_precision,
            "step_recall": step_recall,
            "step_f1": step_f1,
            "total_gt_steps": total_gt_steps,
            "total_pred_steps": total_pred_steps,
            "matched_steps": matched_steps,
            "field_accuracy": field_acc
        }
