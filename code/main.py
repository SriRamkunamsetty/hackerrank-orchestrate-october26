"""
Ghost Data Still Exists: Production-Grade Deletion-Audit Agent Entry Point
Processes all 518 evaluation cases from dataset/deletion_requests.csv
and produces the official submission output.csv at the repository root.
"""
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from code.config import (
    DELETION_REQUESTS_FILE,
    OUTPUT_FILE,
    SAMPLE_DELETION_REQUESTS_FILE,
    SAMPLE_OUTPUT_FILE
)
from code.agent.pipeline import AuditPipeline
from code.utils.logger import get_logger

logger = get_logger("audit_main")

def run_audit(input_file: Path = DELETION_REQUESTS_FILE, output_file: Path = OUTPUT_FILE) -> int:
    """
    Execute deletion audit across all cases in input_file and write sorted output_file.
    Returns the count of successfully processed cases.
    """
    logger.info(f"Starting Ghost Data Still Exists Deletion-Audit Pipeline")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Target output: {output_file}")

    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    start_time = time.time()
    pipeline = AuditPipeline()

    with open(input_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        case_rows = list(reader)

    total_cases = len(case_rows)
    logger.info(f"Loaded {total_cases} deletion requests to audit.")

    results: List[Tuple[str, str, str]] = []
    status_counts = {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0}

    for idx, row in enumerate(case_rows, start=1):
        case_id = row.get("case_id", "").strip()
        cid, status, steps_json = pipeline.process_case(row)
        results.append((cid, status, steps_json))
        status_counts[status] = status_counts.get(status, 0) + 1

        if idx % 50 == 0 or idx == total_cases:
            elapsed = time.time() - start_time
            logger.info(f"Progress: {idx}/{total_cases} ({idx/total_cases*100:.1f}%) | Elapsed: {elapsed:.1f}s")

    # Sort results deterministically by case_id
    def case_sort_key(item: Tuple[str, str, str]):
        cid = item[0]
        # Extract number if pattern case_<num>
        if "_" in cid:
            parts = cid.split("_")
            if parts[-1].isdigit():
                return (parts[0], int(parts[-1]))
        return (cid, 0)

    results.sort(key=case_sort_key)

    # Write output.csv with exact required header
    with open(output_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for cid, status, steps_json in results:
            writer.writerow([cid, status, steps_json])

    total_duration = time.time() - start_time
    logger.info(f"Audit completed in {total_duration:.2f} seconds.")
    logger.info(f"Status distribution: {status_counts}")
    logger.info(f"Output successfully written to {output_file}")

    # Validate output
    validate_output(output_file, expected_count=total_cases)
    return total_cases

def validate_output(output_file: Path, expected_count: int = 518) -> bool:
    """
    Validate that output.csv satisfies all competition contracts:
    - Exact columns: case_id,deletion_status,steps_json
    - Exactly expected_count data rows
    - Valid JSON array for steps_json
    - Valid deletion_status in {COMPLETE, INCOMPLETE, NOT_APPLICABLE}
    - NOT_APPLICABLE has steps_json = []
    """
    logger.info(f"Validating output submission file: {output_file}")
    with open(output_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["case_id", "deletion_status", "steps_json"]:
            raise ValueError(f"Invalid columns: {reader.fieldnames}. Expected ['case_id', 'deletion_status', 'steps_json']")

        rows = list(reader)
        if len(rows) != expected_count:
            raise ValueError(f"Row count mismatch: found {len(rows)}, expected {expected_count}")

        for idx, r in enumerate(rows, start=1):
            cid = r["case_id"]
            st = r["deletion_status"]
            steps_raw = r["steps_json"]

            if st not in {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}:
                raise ValueError(f"Row {idx} ({cid}) has invalid status: {st}")

            try:
                steps = json.loads(steps_raw)
                if not isinstance(steps, list):
                    raise ValueError(f"Row {idx} ({cid}) steps_json is not a list")
            except Exception as e:
                raise ValueError(f"Row {idx} ({cid}) has invalid JSON: {e}")

            if st == "NOT_APPLICABLE" and steps != []:
                raise ValueError(f"Row {idx} ({cid}) is NOT_APPLICABLE but has non-empty steps: {steps}")

    logger.info(f"Validation PASSED! All {expected_count} rows conform strictly to submission contract.")
    return True

if __name__ == "__main__":
    run_audit()
