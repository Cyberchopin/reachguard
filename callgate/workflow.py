"""Trusted local orchestration for a demo action, not real identity enrollment."""
import hashlib
import json
import secrets
import threading
import time
import math
from collections import deque

from .engine import Conversation, WEIGHTS
from .safety_policy import SafetyConversation
from .evidence_graph import evidence_graph
from .receipt import issue_receipt, current_evidence


class ChallengeRateLimited(ValueError):
    def __init__(self, retry_after):
        super().__init__('challenge issuance rate exceeded')
        self.retry_after = retry_after


class DemoWorkflow:
    def __init__(self, coordinator, gate, reviewer, *, request_clock=time.monotonic):
        self._coordinator = coordinator
        self._gate = gate
        self._reviewer = reviewer
        self._conversation = SafetyConversation()
        self._session = secrets.token_hex(16)
        self._pending = None
        self._outcome = None
        self._processing_consent = 'NOT_REQUESTED'
        self._generation = 0
        self._lock = threading.RLock()
        self._request_clock = request_clock
        self._issued = deque()
        self._denied_resources = set()
        self._authorization_denied = False

    def _invalidate(self):
        if self._pending is not None:
            if self._coordinator.expired(self._pending[0]):
                self._authorization_denied = True
            self._coordinator.cancel(self._pending[0].request_id)
        self._pending = None

    def status(self):
        with self._lock:
            if self._pending is not None and self._coordinator.expired(self._pending[0]):
                self._invalidate()
            return {'risk_state': self._conversation.state,
                    'processing_consent': self._processing_consent,
                    'processing_allowed': self._processing_consent == 'GRANTED',
                    'pending': self._pending is not None,
                    'authorization_denied': self._authorization_denied,
                    'outcome': None if self._outcome is None else dict(self._outcome)}

    def telemetry_context(self):
        """Privacy-bounded identifiers for observability, never transcript text."""
        with self._lock:
            return {'session_id': self._session, 'risk_state': self._conversation.state,
                    'pending': self._pending is not None,
                    'authorization_denied': self._authorization_denied}

    def set_processing_consent(self, granted):
        """Apply an explicit per-session processing choice.

        Declining or withdrawing is fail-closed: current evidence and any pending
        action are discarded. This is a product control, not a legal conclusion.
        """
        if type(granted) is not bool:
            raise ValueError('invalid consent choice')
        with self._lock:
            if granted:
                self._processing_consent = 'GRANTED'
            else:
                self._generation += 1
                self._processing_consent = ('REVOKED' if self._processing_consent == 'GRANTED'
                                            else 'DECLINED')
                self._invalidate()
                self._conversation = SafetyConversation()
                self._outcome = None
            return {'processing_consent': self._processing_consent,
                    'processing_allowed': self._processing_consent == 'GRANTED'}

    def reset_session(self):
        """End the current scenario and require fresh consent for a new one."""
        with self._lock:
            self._generation += 1
            self._invalidate()
            self._conversation = SafetyConversation()
            self._session = secrets.token_hex(16)
            self._denied_resources.clear()
            self._authorization_denied = False
            self._outcome = None
            self._processing_consent = 'NOT_REQUESTED'
            return {'risk_state': self._conversation.state,
                    'processing_consent': self._processing_consent,
                    'processing_allowed': False, 'pending': False, 'outcome': None}

    def processing_generation(self):
        with self._lock:
            if self._processing_consent != 'GRANTED':
                raise ValueError('processing consent required')
            return self._generation

    def evidence_view(self):
        """Snapshot current provenance and deduplicated rule contributions."""
        with self._lock:
            snapshot = self._conversation.snapshot()
            kinds = sorted({row['kind'] for row in current_evidence(self._conversation)})
            return {'schema_version': 'callgate-evidence-v1',
                    'graph': evidence_graph(self._conversation),
                    'contributions': [{'kind': k, 'weight': WEIGHTS[k]} for k in kinds],
                    'score': snapshot['score'], 'state': snapshot['state'],
                    'score_kind': 'heuristic_not_probability',
                    'uncertainty': snapshot['uncertainty'],
                    'formula': 'min(100, sum(weight of each distinct final risk category))'}

    def decision_receipt(self, signing_key):
        with self._lock:
            if self._processing_consent != 'GRANTED' or not self._conversation.segments:
                raise ValueError('current consented evidence required')
            return issue_receipt(self._conversation, signing_key, session_id=self._session)

    def ingest(self, transcript, *, generation=None):
        with self._lock:
            if generation is not None and generation != self._generation:
                raise ValueError('stale audio session')
            if self._processing_consent != 'GRANTED':
                raise ValueError('processing consent required')
            result = self._conversation.ingest(transcript)
            if result['status'] == 'accepted':
                self._invalidate()
            return result

    def pending_confirmation(self):
        """Read-only view for the authenticated reviewer transport."""
        with self._lock:
            if self._pending is not None and self._coordinator.expired(self._pending[0]):
                self._invalidate()
            if self._pending is None:
                return None
            request, operation, _, _ = self._pending
            return {'request': request.model_dump(), 'operation': dict(operation)}

    def binding_context(self):
        """Local operator snapshot; never exposed by the device inbox."""
        with self._lock:
            return {'session_id': self._session, **self.status()}

    def request_bound_confirmation(self, *, session_id, **operation):
        """Atomic local binding check followed by the original challenge path."""
        with self._lock:
            if session_id != self._session:
                raise ValueError('bound session changed; bind the current session again')
            if self._processing_consent != 'GRANTED':
                raise ValueError('processing consent required')
            if self.status()['pending']:
                raise ValueError('another confirmation is pending; it will not be replaced')
            return self.request_confirmation(**operation)

    def contact_identities(self):
        return self._coordinator.contact_identities()

    def request_confirmation(self, *, destination, amount_cents, claimed_identity=None):
        # Operation comes from the trusted application, never extracted speech.
        if not isinstance(destination, str) or not destination.strip() or len(destination) > 80:
            raise ValueError('invalid destination')
        if type(amount_cents) is not int or not 0 < amount_cents <= 100_000_000:
            raise ValueError('invalid amount')
        if claimed_identity is not None and (not isinstance(claimed_identity, str)
                or not claimed_identity or len(claimed_identity) > 80):
            raise ValueError('invalid claimed identity')
        with self._lock:
            if self._conversation.state != 'CHALLENGED':
                raise ValueError('policy requires a challenged conversation')
            if self._pending is not None and self._coordinator.expired(self._pending[0]):
                self._authorization_denied = True
                self._invalidate()
            if self._authorization_denied:
                raise ValueError('authorization denied for this session')
            now = self._request_clock()
            while self._issued and self._issued[0] <= now - 3600:
                self._issued.popleft()
            recent = [t for t in self._issued if t > now - 60]
            waits = []
            if len(recent) >= 5:
                waits.append(recent[0] + 60 - now)
            if len(self._issued) >= 30:
                waits.append(self._issued[0] + 3600 - now)
            if waits:
                raise ChallengeRateLimited(max(1, math.ceil(max(waits))))
            operation = dict(destination=destination, amount_cents=amount_cents, currency='USD')
            if claimed_identity is not None:
                operation['claimed_identity'] = claimed_identity
            resource = hashlib.sha256(json.dumps(operation, sort_keys=True).encode()).hexdigest()
            if resource in self._denied_resources:
                raise ValueError('operation denied for this session')
            self._invalidate()
            request = self._coordinator.create(session_id=self._session, resource=resource,
                reviewer=self._reviewer, claimed_identity=claimed_identity)
            challenge = f'{secrets.randbelow(1_000_000):06d}'
            challenge_digest = hashlib.sha256(
                (self._session + request.request_id + challenge).encode()).digest()
            self._pending = (request, operation, challenge_digest, 0)
            self._issued.append(now)
            self._outcome = None
            return {'request': request, 'operation': dict(operation),
                    'out_of_band_challenge': challenge}

    def complete(self, decision, *, challenge_response=None):
        with self._lock:
            if self._pending is None or decision.request != self._pending[0]:
                raise ValueError('no matching current confirmation')
            if self._conversation.state != 'CHALLENGED':
                raise ValueError('policy denies action')
            request, operation, expected_challenge, attempts = self._pending
            if self._coordinator.expired(request):
                self._authorization_denied = True
                self._invalidate()
                raise ValueError('confirmation expired; authorization denied for this session')
            if decision.approved:
                supplied = '' if challenge_response is None else str(challenge_response)
                actual = hashlib.sha256(
                    (self._session + request.request_id + supplied).encode()).digest()
                if not secrets.compare_digest(actual, expected_challenge):
                    attempts += 1
                    if attempts >= 3:
                        self._authorization_denied = True
                        self._invalidate()
                    else:
                        self._pending = (request, operation, expected_challenge, attempts)
                    raise ValueError('invalid out-of-band challenge')
            credential = self._coordinator.decide(decision)
            self._pending = None
            if credential is None:
                self._authorization_denied = True
                self._denied_resources.add(request.resource)
                self._outcome = {'status': 'reviewer_denied', 'real_action_executed': False}
                return dict(self._outcome)
            result = self._gate.execute(credential, session_id=self._session,
                resource=request.resource, human_confirmed=True, policy_allows=True)
            self._outcome = {**result, 'operation': dict(operation)}
            return dict(self._outcome)
