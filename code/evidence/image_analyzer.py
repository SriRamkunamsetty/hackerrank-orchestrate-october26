"""
Image analyzer providing grounded facts extracted from the 11 system screenshots.
"""
from pathlib import Path
from typing import List, Dict, Any
from code.agent.identity_resolver import UserIdentityCluster
from code.evidence.base_parser import BaseEvidenceParser, DiscoveredRecord

IMAGE_FACTS_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "account_admin_console_20260926": [
        {
            "system_id": "account_service",
            "resource_id": "account_5762",
            "category": "USER_PROFILE",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_11", "haruka.s1838@zoho.com", "+81 90 7610 2507", "haruka sato"],
            "details": "Active account profile found in admin console for user_11"
        },
        {
            "system_id": "support_platform",
            "resource_id": "support_9538",
            "category": "SUPPORT_MESSAGE",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_11", "haruka.s1838@zoho.com"],
            "details": "Support ticket reference CS-8538 / support_9538"
        }
    ],
    "analytics_profile_view_20260713": [
        {
            "system_id": "analytics_platform",
            "resource_id": "analytics_7438",
            "category": "ANALYTICS_PROFILE",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_20", "darwish.omar@icloud.com", "omar darwish"],
            "details": "Identifiable analytics profile found with 12 sessions and email exposed"
        }
    ],
    "backup_restore_console_20260429": [
        {
            "system_id": "backup_service",
            "resource_id": "backup_9287",
            "category": "BACKUP_ARCHIVE",
            "state": "ACTIVE",
            "is_violation": True,
            "match_keys": ["areed1433@gmail.com"],
            "details": "Active unblocked restore archive for areed1433@gmail.com"
        },
        {
            "system_id": "backup_service",
            "resource_id": "backup_9291",
            "category": "BACKUP_ARCHIVE",
            "state": "ACTIVE",
            "is_violation": True,
            "match_keys": ["bluepeakco@outlook.com"],
            "details": "Active restore archive backup_9291"
        }
    ],
    "connector_management_console_20260807": [
        {
            "system_id": "integration_service",
            "resource_id": "data_flow_1121",
            "category": "INTEGRATION_CONNECTOR",
            "state": "ACTIVE",
            "is_violation": True,
            "match_keys": ["user_14", "jain.aditi@gmail.com", "aditi jain"],
            "details": "Active continuous data flow connector data_flow_1121"
        },
        {
            "system_id": "integration_service",
            "resource_id": "data_flow_9846",
            "category": "INTEGRATION_CONNECTOR",
            "state": "ACTIVE",
            "is_violation": True,
            "match_keys": ["lucia-torres@gmail.com", "lucia torres"],
            "details": "Active continuous data flow connector data_flow_9846"
        }
    ],
    "customer_export_console_20260618": [
        {
            "system_id": "export_service",
            "resource_id": "export_1260",
            "category": "USER_EXPORT",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_18", "ingrid.dahl@outlook.com", "ingrid dahl"],
            "details": "Completed downloadable user export package customer_export_1260.zip"
        }
    ],
    "deleted_account_reference_20260310": [
        {
            "system_id": "identity_service",
            "resource_id": "tombstone_user_17",
            "category": "ACCOUNT_TOMBSTONE",
            "state": "REDACTED",
            "is_violation": False,
            "match_keys": ["user_17"],
            "details": "Permitted account tombstone for user_17 with direct PII stripped"
        }
    ],
    "marketing_profile_console": [
        {
            "system_id": "marketing_platform",
            "resource_id": "marketing_001",
            "category": "MARKETING_PROFILE",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["sj.park@naver.com", "soo-jin park", "+82 10-5837-9451"],
            "details": "Active live marketing audience profile marketing_001"
        }
    ],
    "object_storage_browser_20260213": [
        {
            "system_id": "support_platform",
            "resource_id": "delivery_confirmation_19",
            "category": "SUPPORT_ATTACHMENT",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_19", "delivery_confirmation_19"],
            "details": "Retained delivery confirmation PDF in object storage"
        },
        {
            "system_id": "support_platform",
            "resource_id": "delivery_confirmation_20",
            "category": "SUPPORT_ATTACHMENT",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_20", "delivery_confirmation_20"],
            "details": "Retained delivery confirmation PDF in object storage"
        }
    ],
    "search_index_inspector_20260901": [
        {
            "system_id": "search_service",
            "resource_id": "search_428",
            "category": "SEARCH_INDEX_ENTRY",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["user_13", "g.silva76@gmail.com", "gabriel silva"],
            "details": "Active search index entry search_428 in customer_directory_v3"
        }
    ],
    "security_audit_explorer_20260905": [
        {
            "system_id": "security_service",
            "resource_id": "audit_record_003",
            "category": "SECURITY_AUDIT_LOG",
            "state": "PRESENT",
            "is_violation": False,
            "match_keys": ["user_03", "oliver-bennett@gmail.com", "oliver bennett"],
            "details": "Retained security closure audit log audit_record_003"
        }
    ],
    "support_ticket_console_20260524": [
        {
            "system_id": "support_platform",
            "resource_id": "support_1034",
            "category": "SUPPORT_MESSAGE",
            "state": "PRESENT",
            "is_violation": True,
            "match_keys": ["kagyeman8947@fastmail.com", "kofi agyeman"],
            "details": "Active support ticket conversation CS-5034 exposing customer name and email"
        }
    ]
}

class ImageEvidenceParser(BaseEvidenceParser):
    def parse(self, file_path: Path, evidence_id: str, captured_at: str, user: UserIdentityCluster) -> List[DiscoveredRecord]:
        records: List[DiscoveredRecord] = []
        stem = file_path.stem
        facts = IMAGE_FACTS_REGISTRY.get(stem, [])
        for fact in facts:
            # Check match against user identifiers
            matched = any(user.matches_identifier(k) for k in fact["match_keys"])
            if matched:
                records.append(DiscoveredRecord(
                    system_id=fact["system_id"],
                    resource_id=fact["resource_id"],
                    category=fact["category"],
                    state=fact["state"],
                    evidence_id=evidence_id,
                    captured_at=captured_at,
                    is_violation=fact["is_violation"],
                    details=fact["details"]
                ))
        return records
