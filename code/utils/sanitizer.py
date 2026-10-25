"""
Sanitizer utility to redact sensitive personal data in logs and LLM prompts.
"""
import re

EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-\(\)]{7,}\d)")

def sanitize_pii(text: str) -> str:
    """
    Mask personal identifiable information (PII) such as email and phone.
    """
    if not text:
        return ""
    
    # Redact email addresses to user***@domain.com
    def mask_email(match):
        user, domain = match.group(1), match.group(2)
        if len(user) <= 2:
            masked_user = user[0] + "***"
        else:
            masked_user = user[:2] + "***" + user[-1]
        return f"{masked_user}@{domain}"

    sanitized = EMAIL_PATTERN.sub(mask_email, text)
    sanitized = PHONE_PATTERN.sub(r"[PHONE REDACTED]", sanitized)
    return sanitized
