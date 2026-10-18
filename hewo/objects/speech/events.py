"""Thread-safe status messages consumed by the Pygame update loop."""

from dataclasses import dataclass
from enum import Enum


class SpeechEventKind(str, Enum):
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass(frozen=True)
class SpeechEvent:
    kind: SpeechEventKind
    text: str
    error: str | None = None
