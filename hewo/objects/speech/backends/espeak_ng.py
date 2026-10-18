"""Small command-line adapter for the locally installed eSpeak NG engine."""

import shutil
import subprocess

from hewo.objects.speech.engine import SpeechAudio


class EspeakNgEngine:
    """Synthesize WAV bytes by invoking ``espeak-ng`` as a subprocess."""

    def __init__(self, voice: str = "es"):
        executable = shutil.which("espeak-ng")
        if executable is None:
            raise RuntimeError("espeak-ng executable was not found on PATH")
        self.executable = executable
        self.voice = voice

    def synthesize(self, text: str) -> SpeechAudio:
        result = subprocess.run(
            [self.executable, "--stdout", "--voice", self.voice, text],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return SpeechAudio(result.stdout)

    def close(self) -> None:
        """eSpeak NG uses a short-lived process, so there is nothing to release."""
