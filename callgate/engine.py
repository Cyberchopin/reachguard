"""Deterministic English baseline. Scores are heuristic, never probabilities."""
import re
from typing import Protocol
from .models import Transcript, RiskEvent

PATTERNS = {
    "authority": r"\b(?:calling from|this is (?:the |your )?(?:bank|police|irs)|financial aid|i am your grandson)\b",
    "urgency": r"\b(?:right now|immediately|tonight|urgent|within \d+ minutes|arrest|enrollment.{0,15}cancelled)\b",
    "secrecy": r"\b(?:don't tell|do not tell|keep (?:this|it) secret|between us|tell no one)\b",
    "money": r"\b(?:send|transfer|wire|pay|zelle|buy)\b.{0,50}\b(?:money|\d[\d,]*|gift cards?|bitcoin|crypto|dollars)\b",
    "credentials": r"\b(?:tell|read|share|send|give|provide|reveal|disclose|forward|enter|type|what is)\b[^.!?;\n]{0,40}\b(?:otp|password|passcode|pin|verification code|one.time (?:code|password)|security code|authentication code|six.digit code|6.digit code|2fa code)\b",
    "remote_access": r"\b(?:install|download|open)\b.{0,30}\b(?:anydesk|teamviewer|remote access)\b",
    "injection": r"\b(?:ignore (?:all |previous )?(?:rules|instructions)|mark (?:me |this )?verified|disable (?:guardian|safety))\b",
}
WEIGHTS = dict(authority=10, urgency=15, secrecy=20, money=35, credentials=60, remote_access=45, injection=30)
HIGH_IMPACT = {"money", "credentials", "remote_access"}
EXTRACTOR_VERSION = "rules-en-v4"


def educational_spans(text):
    """Narrow explicit hypothetical examples; quotation marks alone prove nothing.

    End at sentence or contrast boundaries so a subsequent live request is kept.
    This is a development heuristic, not a speaker-intent classifier.
    """
    pattern = (r"\b(?:a|the) scammer (?:might|may|could) say\s*:\s*"
               r"[^.!?;\n]*?(?=\b(?:but|however|instead|now you)\b|[.!?;\n]|$)")
    return [(m.start(), m.end()) for m in re.finditer(pattern, text, re.I)]

# A bounded request grammar: asset relocation can avoid the word "money".
# Anchor to a sentence/request prefix so ordinary first-person plans and
# conditional educational discussion do not become transfer requests.
ASSET_REQUEST = (
    r"(?:^|[.!?;]\s*)(?:please\s+|you (?:need|have) to\s+|"
    r"(?:can|could|would|will) you\s+)?"
    r"(?:move|shift|relocate|transfer|send|deposit)\s+"
    r"(?:(?:all|some) of\s+)?(?:your|the)\s+"
    r"(?:savings|funds|balance|money|cash|assets)\s+"
    r"(?:to|into)\s+[^.!?;\n]{0,65}\b(?:wallet|account)\b"
)


class Extractor(Protocol):
    def extract(self, segment: Transcript) -> list[RiskEvent]: ...


class RuleExtractor:
    def extract(self, segment):
        if segment.role == "recipient" or segment.language != "en":
            return []
        events = []
        examples = educational_spans(segment.text)
        for kind, pattern in [*PATTERNS.items(), ("money", ASSET_REQUEST)]:
            for match in re.finditer(pattern, segment.text, re.I):
                if any(start <= match.start() and match.end() <= end for start, end in examples):
                    continue
                # Local negation only: documented baseline limitation, not semantic understanding.
                prefix = segment.text[max(0, match.start()-20):match.start()].lower()
                if kind in HIGH_IMPACT and re.search(r"(?:don't|do not|never|won't|will not)\s+$", prefix):
                    continue
                if any(e.kind == kind and e.start < match.end() and match.start() < e.end for e in events):
                    continue
                events.append(RiskEvent(event_id=f"{segment.segment_id}:{segment.revision}:{kind}:{match.start()}",
                    segment_id=segment.segment_id, revision=segment.revision, kind=kind,
                    start=match.start(), end=match.end(), confidence=0.7, extractor=EXTRACTOR_VERSION))
        return events


class Conversation:
    def __init__(self, extractor: Extractor | None = None):
        self.extractor = extractor or RuleExtractor()
        self.segments = {}
        self.events = {}
        self.timeline = []
        self.state = "UNVERIFIED"
        self.intervention_key = None

    def ingest(self, segment: Transcript):
        old = self.segments.get(segment.segment_id)
        if old:
            if segment == old or segment.revision < old.revision:
                return self.snapshot("ignored")
            if segment.revision == old.revision:
                raise ValueError("conflicting revision")
            if old.final and not segment.final:
                raise ValueError("final segment cannot become partial")
        if len(self.timeline) >= 2000 or (old is None and len(self.segments) >= 500):
            raise ValueError("session capacity reached; start a new session")
        # Validate all candidate evidence before mutating any session state.
        candidates = [RiskEvent.model_validate(e.model_dump() if isinstance(e, RiskEvent) else e)
                      for e in self.extractor.extract(segment)]
        for e in candidates:
            if e.segment_id != segment.segment_id or e.revision != segment.revision or not 0 <= e.start < e.end <= len(segment.text):
                raise ValueError("invalid evidence reference")
        self.segments[segment.segment_id] = segment
        self.events[segment.segment_id] = candidates
        committed = {e.kind for sid, events in self.events.items() if self.segments[sid].final for e in events}
        provisional = {e.kind for events in self.events.values() for e in events}
        if "credentials" in committed:
            self.state = "BLOCKED"
        elif self.state != "BLOCKED" and "secrecy" in committed and HIGH_IMPACT & committed:
            self.state = "COOLING_OFF"
        elif self.state not in {"BLOCKED", "COOLING_OFF"}:
            self.state = "CHALLENGED" if HIGH_IMPACT & committed else "UNVERIFIED"
        score = min(100, sum(WEIGHTS[k] for k in committed))
        self.timeline.append(dict(sequence=len(self.timeline), audio_ms=segment.end_ms,
            segment_id=segment.segment_id, revision=segment.revision, score=score,
            provisional_score=min(100, sum(WEIGHTS[k] for k in provisional)), state=self.state))
        return self.snapshot("accepted")

    def snapshot(self, status="snapshot"):
        events = [e.model_dump() for ev in self.events.values() for e in ev]
        messages = {
            "UNVERIFIED": ("LISTEN", "Keep listening. Identity has not been verified."),
            "CHALLENGED": ("VERIFY", "Pause this action. Call back using a number you already trust."),
            "COOLING_OFF": ("PAUSE", "Take time away from this call. Verify independently before taking action."),
            "BLOCKED": ("DO_NOT_SHARE", "Do not share passwords or verification codes. Use a known contact channel."),
        }
        action, message = messages[self.state]
        key = self.state
        emit = status == "accepted" and key != self.intervention_key and self.state != "UNVERIFIED"
        if status == "accepted":
            self.intervention_key = key
        return dict(status=status, state=self.state, events=events, timeline=list(self.timeline),
            score=self.timeline[-1]["score"] if self.timeline else 0,
            score_kind="heuristic_not_probability", policy_version="v2-phase1", extractor=EXTRACTOR_VERSION,
            guardian=dict(action=action, message=message, emit=emit, mode="advisory"),
            uncertainty=sorted({"unsupported_language" for s in self.segments.values() if s.language != "en"}
                | {"educational_context_heuristic" for s in self.segments.values() if educational_spans(s.text)}
                | {"speaker_role_unknown" for s in self.segments.values() if s.role == "unknown"}),
            protected_actions_allowed=False)
