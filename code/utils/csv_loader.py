"""
CSV loader module with robust type casting, sanitization, and encoding management.
"""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

def load_csv(file_path: Path) -> List[Dict[str, str]]:
    """
    Safely load a CSV file into a list of dictionaries with normalized keys and values.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    records = []
    with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized_row = {
                (k.strip() if k else ""): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
                if k is not None
            }
            records.append(normalized_row)
    return records

def write_csv(file_path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """
    Safely write rows to a CSV file.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
