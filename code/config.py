"""
Central configuration for Ghost Data Still Exists deletion audit agent.
"""
import os
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"
OUTPUT_FILE = REPO_ROOT / "output.csv"
LOG_FILE = REPO_ROOT / "log.txt"

# Dataset Input Files
DELETION_REQUESTS_FILE = DATASET_DIR / "deletion_requests.csv"
SAMPLE_DELETION_REQUESTS_FILE = DATASET_DIR / "sample_deletion_requests.csv"
SAMPLE_OUTPUT_FILE = DATASET_DIR / "sample_output.csv"
USER_IDENTITIES_FILE = DATASET_DIR / "user_identities.csv"
USER_AUDIT_LOG_FILE = DATASET_DIR / "user_audit_log.csv"
SYSTEM_ACTIVITY_FILE = DATASET_DIR / "system_activity.csv"
DELETION_RULES_FILE = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_FILES_MANIFEST = DATASET_DIR / "evidence_files.csv"
EVIDENCE_FILES_FILE = EVIDENCE_FILES_MANIFEST

# LLM Configuration (Read strictly from environment variables - never hardcode)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")

# Processing Configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "16"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"

# Canonical Phase & Operation Ordering (Contractual Invariant)
PHASE_ORDER = {
    "FINDING": 0,
    "REMEDIATION": 1,
    "VERIFICATION": 2,
}

OPERATION_ORDER = {
    # Findings
    "REPORT_REMAINING_RECORD": 0,
    "REPORT_EXPOSED_PII": 1,
    "REPORT_ACTIVE_DATA_FLOW": 2,
    "REPORT_RESTORE_RISK": 3,
    # Remediation
    "DISABLE_DATA_FLOW": 4,
    "BLOCK_RESTORE": 5,
    "DELETE_RECORD": 6,
    "REDACT_RECORD": 7,
    "ANONYMIZE_RECORD": 8,
    # Verification
    "VERIFY_RECORD_ABSENT": 9,
    "VERIFY_RECORD_PRESENT": 10,
    "VERIFY_RECORD_REDACTED": 11,
    "VERIFY_RECORD_ANONYMIZED": 12,
    "VERIFY_DATA_FLOW_DISABLED": 13,
    "VERIFY_RESTORE_BLOCKED": 14,
}

OPERATION_STATE_MAP = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}
