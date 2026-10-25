"""
Identity resolver using Union-Find to merge current identities and historical audit logs.
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, List, Optional
from code.config import USER_IDENTITIES_FILE, USER_AUDIT_LOG_FILE
from code.utils.csv_loader import load_csv

@dataclass
class UserIdentityCluster:
    user_id: str
    primary_email: str
    emails: Set[str] = field(default_factory=set)
    names: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    email_hashes: Set[str] = field(default_factory=set)
    audit_events: List[Dict[str, str]] = field(default_factory=list)

    def matches_identifier(self, identifier: str) -> bool:
        """
        Check if an arbitrary string matches any known email, phone, name, hash, or user_id.
        """
        if not identifier:
            return False
        clean = identifier.strip().lower()
        if clean == self.user_id.lower():
            return True
        if clean in {e.lower() for e in self.emails}:
            return True
        # Normalize phones (strip whitespace, hyphens, brackets)
        norm_phone = "".join(c for c in clean if c.isdigit())
        for p in self.phones:
            if norm_phone and norm_phone == "".join(c for c in p if c.isdigit()):
                return True
        if clean in {h.lower() for h in self.email_hashes}:
            return True
        for name in self.names:
            if clean == name.lower():
                return True
        return False

class IdentityResolver:
    """
    Builds and queries the connected identity graph for Northstar Shop customers.
    """
    def __init__(self, identities_path: Path = USER_IDENTITIES_FILE, audit_log_path: Path = USER_AUDIT_LOG_FILE):
        self.identities_path = identities_path
        self.audit_log_path = audit_log_path
        self.user_clusters: Dict[str, UserIdentityCluster] = {}
        self.email_to_userid: Dict[str, str] = {}
        self.phone_to_userid: Dict[str, str] = {}
        self.hash_to_userid: Dict[str, str] = {}
        self._build_graph()

    def _build_graph(self):
        # 1. Ingest baseline current identities
        identities_rows = load_csv(self.identities_path)
        for row in identities_rows:
            uid = row["user_id"].strip()
            name = row.get("name", "").strip()
            email = row.get("email", "").strip()
            phone = row.get("phone", "").strip()
            e_hash = row.get("email_hash", "").strip()

            cluster = UserIdentityCluster(user_id=uid, primary_email=email)
            if email:
                cluster.emails.add(email)
                self.email_to_userid[email.lower()] = uid
                # Also generate SHA-256 hash if not present
                computed_hash = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()
                cluster.email_hashes.add(computed_hash)
                self.hash_to_userid[computed_hash.lower()] = uid
            if name:
                cluster.names.add(name)
            if phone:
                cluster.phones.add(phone)
                self.phone_to_userid[phone.strip()] = uid
            if e_hash:
                cluster.email_hashes.add(e_hash)
                self.hash_to_userid[e_hash.lower()] = uid

            self.user_clusters[uid] = cluster

        # 2. Ingest historical audit logs and link historical identifiers
        audit_rows = load_csv(self.audit_log_path)
        for row in audit_rows:
            uid = row.get("user_id", "").strip()
            field_name = row.get("field_name", "").strip()
            old_val = row.get("old_value", "").strip()
            new_val = row.get("new_value", "").strip()

            if uid in self.user_clusters:
                cluster = self.user_clusters[uid]
                cluster.audit_events.append(row)

                for val in [old_val, new_val]:
                    if not val:
                        continue
                    if field_name == "email":
                        cluster.emails.add(val)
                        self.email_to_userid[val.lower()] = uid
                        computed = hashlib.sha256(val.lower().encode("utf-8")).hexdigest()
                        cluster.email_hashes.add(computed)
                        self.hash_to_userid[computed.lower()] = uid
                    elif field_name == "phone":
                        cluster.phones.add(val)
                        self.phone_to_userid[val.strip()] = uid
                    elif field_name == "email_hash":
                        cluster.email_hashes.add(val)
                        self.hash_to_userid[val.lower()] = uid
                    elif field_name == "name":
                        cluster.names.add(val)

    def resolve_by_email(self, email: str) -> Optional[UserIdentityCluster]:
        if not email:
            return None
        norm_email = email.strip().lower()
        uid = self.email_to_userid.get(norm_email)
        if uid and uid in self.user_clusters:
            return self.user_clusters[uid]
        return None

    def resolve_by_user_id(self, user_id: str) -> Optional[UserIdentityCluster]:
        if not user_id:
            return None
        return self.user_clusters.get(user_id.strip())

    def resolve_by_phone(self, phone: str) -> Optional[UserIdentityCluster]:
        if not phone:
            return None
        clean_phone = phone.strip()
        uid = self.phone_to_userid.get(clean_phone)
        if uid and uid in self.user_clusters:
            return self.user_clusters[uid]
        return None

    def resolve_by_hash(self, email_hash: str) -> Optional[UserIdentityCluster]:
        if not email_hash:
            return None
        clean_hash = email_hash.strip().lower()
        uid = self.hash_to_userid.get(clean_hash)
        if uid and uid in self.user_clusters:
            return self.user_clusters[uid]
        return None
