"""Audio output implementations, kept separate from speech engines."""

from io import BytesIO
import time
from typing import Protocol

import pygame

from hewo.objects.speech.engine import SpeechAudio


class AudioOutput(Protocol):
    """Play synthesized audio; ``play`` blocks until playback ends or stops."""

    def play(self, audio: SpeechAudio) -> None:
        ...

    def stop(self) -> None:
        ...

    def close(self) -> None:
        ...


class PygameAudioOutput:
    """Playback adapter using the application's existing Pygame mixer."""

    def __init__(self):
        self._channel = None

    def play(self, audio: SpeechAudio) -> None:
        if not pygame.mixer.get_init():
            raise RuntimeError("Pygame mixer is not initialized")

        sound = pygame.mixer.Sound(file=BytesIO(audio.wav_data))
        self._channel = sound.play()
        if self._channel is None:
            raise RuntimeError("No free Pygame mixer channel for speech playback")

        while self._channel.get_busy():
            time.sleep(0.01)
        self._channel = None

    def stop(self) -> None:
        if self._channel is not None:
            self._channel.stop()
            self._channel = None

    def close(self) -> None:
        self.stop()
