"""
Request classifier determining whether a request authorizes personal data deletion.
Distinguishes genuine deletion requests from non-deletion requests (access, export, rectification).
"""
import re
from typing import Tuple

NON_DELETION_PHRASES = [
    "leave the account active",
    "not asking for deletion",
    "keep the account as it is",
    "keep the account",
    "do not close the account",
    "don't close the account",
    "without removing any",
    "marketing lists only",
    "marketing only",
    "not a request to erase",
    "leave my profile",
    "continue using the service",
    "don't delete or change",
    "do not delete or change",
    "portable format",
    "copy of last year",
    "resetting the login",
    "misspelled",
    "information request",
    "i still use it",
]

DELETION_KEYWORDS = [
    # English variations
    r"\b(delet\w*|eras\w*|remov\w*|clos\w*|cancel\w*|purged?|purging)\b",
    # French
    r"\b(suppress\w*|supprim\w*)\b",
    # Spanish
    r"\b(elimin\w*|borr\w*)\b",
    # Portuguese
    r"\b(exclus\w*|excluir\w*|apagar\w*)\b",
    # Specific verification / de-identification terminology
    r"\b(gone|clean\w*|de-identif\w*)\b",
    # Japanese
    r"(削除|解約)",
    # Korean
    r"(삭제|해지)",
]

DELETION_REGEX = re.compile("|".join(DELETION_KEYWORDS), re.IGNORECASE | re.UNICODE)

class RequestClassifier:
    """
    Classifies whether request_text represents an authorized deletion request.
    Returns (is_deletion_authorized: bool, reason: str).
    """
    @staticmethod
    def is_deletion_authorized(request_text: str) -> Tuple[bool, str]:
        if not request_text:
            return False, "EMPTY_REQUEST_TEXT"

        text_lower = request_text.lower()

        # Check explicit non-deletion exclusion phrases first
        for phrase in NON_DELETION_PHRASES:
            if phrase in text_lower:
                return False, f"EXPLICIT_NON_DELETION_INTENT: {phrase}"

        # Check presence of deletion intent
        if DELETION_REGEX.search(request_text):
            return True, "AUTHORIZED_DELETION_INTENT"

        return False, "NO_DELETION_INTENT_DETECTED"
