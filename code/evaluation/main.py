"""
Runner script for evaluation of Ghost Data Still Exists.
Executes AuditPipeline on dataset/sample_deletion_requests.csv, writes temporary
predictions, and computes benchmark metrics against dataset/sample_output.csv.
"""
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure root directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from code.config import SAMPLE_DELETION_REQUESTS_FILE, SAMPLE_OUTPUT_FILE
from code.agent.pipeline import AuditPipeline
from code.evaluation.evaluator import DeletionAuditEvaluator
from code.utils.logger import get_logger

logger = get_logger("evaluation")

def run_evaluation() -> dict:
    logger.info("Initializing AuditPipeline for evaluation on public sample cases...")
    pipeline = AuditPipeline()
    evaluator = DeletionAuditEvaluator(SAMPLE_OUTPUT_FILE)

    sample_cases = []
    with open(SAMPLE_DELETION_REQUESTS_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sample_cases = list(reader)

    logger.info(f"Loaded {len(sample_cases)} sample cases from {SAMPLE_DELETION_REQUESTS_FILE}")

    # Generate predictions
    temp_pred_path = REPO_ROOT / "code" / "evaluation" / "temp_sample_predictions.csv"
    with open(temp_pred_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for row in sample_cases:
            cid, status, steps_json = pipeline.process_case(row)
            writer.writerow([cid, status, steps_json])

    # Evaluate
    metrics = evaluator.evaluate_predictions(temp_pred_path)
    
    # Clean up temp file
    if temp_pred_path.exists():
        temp_pred_path.unlink()

    # Print summary report
    print("\n" + "="*70)
    print("           HACKERRANK ORCHESTRATE: EVALUATION REPORT")
    print("="*70)
    print(f"Total Cases Evaluated:       {metrics['total_cases']}")
    print(f"Case-Level Status Accuracy:  {metrics['status_accuracy']*100:.2f}% ({metrics['status_matches']}/{metrics['total_cases']})")
    print(f"Sequence Accuracy:           {metrics['sequence_accuracy']*100:.2f}% ({metrics['sequence_matches']}/{metrics['total_cases']})")
    print(f"Step Precision:              {metrics['step_precision']*100:.2f}%")
    print(f"Step Recall:                 {metrics['step_recall']*100:.2f}%")
    print(f"Step F1-Score:               {metrics['step_f1']*100:.2f}%")
    print("\nField-Level Accuracy (for matched steps):")
    for field, acc in metrics["field_accuracy"].items():
        print(f"  - {field:<15}: {acc*100:.2f}%")
    print("="*70 + "\n")

    return metrics

if __name__ == "__main__":
    run_evaluation()
