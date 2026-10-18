"""Speech synthesis and playback adapters for HeWo."""

from hewo.objects.speech.controller import SpeechController
from hewo.objects.speech.engine import SpeechAudio, SpeechEngine
from hewo.objects.speech.events import SpeechEvent, SpeechEventKind

__all__ = [
    "SpeechAudio",
    "SpeechController",
    "SpeechEngine",
    "SpeechEvent",
    "SpeechEventKind",
]
