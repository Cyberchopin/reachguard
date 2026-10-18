"""Saved contact routes provisioned by trusted startup, never by caller speech.

Credential origins describe trusted enrollment records, not browser Origin headers
or proof that different physical people control the credentials.
"""
from pydantic import Field
from cryptography.hazmat.primitives import serialization
from .models import StrictModel


class SavedContact(StrictModel):
    identity: str = Field(min_length=1, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    reviewer: str = Field(min_length=1, max_length=80)
    credential_origin: str = Field(min_length=1, max_length=80)


class ContactDirectory:
    def __init__(self, contacts):
        self._contacts = {}
        reviewers = set()
        for row in contacts:
            contact = SavedContact.model_validate(row)
            if contact.identity in self._contacts or contact.reviewer in reviewers:
                raise ValueError('duplicate saved identity or reviewer')
            self._contacts[contact.identity] = contact
            reviewers.add(contact.reviewer)
        if not self._contacts:
            raise ValueError('saved contacts required')

    def validate_keys(self, keys):
        seen = set()
        for contact in self._contacts.values():
            if contact.reviewer not in keys:
                raise ValueError('saved contact key missing')
            raw = keys[contact.reviewer].public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            if raw in seen:
                raise ValueError('shared contact signing key')
            seen.add(raw)

    def identities(self):
        return sorted(self._contacts)

    def resolve(self, identity, initiator_origin):
        contact = self._contacts.get(identity)
        if contact is None:
            raise ValueError('unknown saved identity; no fallback reviewer')
        if not initiator_origin or contact.credential_origin == initiator_origin:
            raise ValueError('self-approval credential origin rejected')
        return contact.reviewer
