"""Contracts shared by interchangeable speech synthesis backends."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SpeechAudio:
    """Encoded WAV audio returned by a speech engine."""

    wav_data: bytes

    def __post_init__(self):
        if not self.wav_data:
            raise ValueError("wav_data cannot be empty")


class SpeechEngine(Protocol):
    """Synthesize text without owning audio playback or UI state."""

    def synthesize(self, text: str) -> SpeechAudio:
        """Return synthesized audio as WAV bytes."""

    def close(self) -> None:
        """Release engine resources, if any."""
