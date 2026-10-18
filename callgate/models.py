from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Transcript(StrictModel):
    segment_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    revision: int = Field(default=0, ge=0)
    text: str = Field(max_length=8000)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    final: bool = False
    role: Literal["caller", "recipient", "unknown"] = "unknown"
    provider_speaker: str | None = Field(default=None, max_length=16, pattern=r"^[A-Za-z0-9_-]+$")
    language: str = Field(default="en", max_length=16)

    @model_validator(mode="after")
    def timestamps(self):
        if self.end_ms < self.start_ms:
            raise ValueError("end_ms must follow start_ms")
        return self


Kind = Literal["authority", "urgency", "secrecy", "money", "credentials", "remote_access", "injection"]


class RiskEvent(StrictModel):
    event_id: str
    segment_id: str
    revision: int
    kind: Kind
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    extractor: str = "rules-en-v2"


class Replay(StrictModel):
    segments: list[Transcript] = Field(min_length=1, max_length=500)
