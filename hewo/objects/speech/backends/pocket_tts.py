"""Local Kyutai Pocket TTS adapter."""

from io import BytesIO
import wave

import numpy as np

from hewo.objects.speech.engine import SpeechAudio


class PocketTTSEngine:
    """Generate WAV audio locally using Kyutai's Pocket TTS.

    Importing this adapter does not import PyTorch or load model weights. The
    optional ``pocket-tts`` dependency and model are loaded on construction.
    """

    def __init__(
        self,
        language: str = "english",
        voice: str | None = None,
        quantize: bool = False,
        sampler_decode_steps: int = 1,
    ):
        try:
            from pocket_tts import TTSModel
            from pocket_tts.default_parameters import get_default_voice_for_language
        except ImportError as error:
            raise RuntimeError(
                "Pocket TTS is optional; install it with `uv sync --extra speech`"
            ) from error

        self.model = TTSModel.load_model(
            language=language,
            quantize=quantize,
            sampler_decode_steps=sampler_decode_steps,
        )
        self.sample_rate = self.model.sample_rate
        if voice is None:
            voice = get_default_voice_for_language(language)
        self.voice_state = self.model.get_state_for_audio_prompt(voice)

    def synthesize(self, text: str) -> SpeechAudio:
        audio = self.model.generate_audio(self.voice_state, text)
        # Pocket TTS returns a mono float tensor. Convert to PCM16 WAV without
        # depending on scipy or writing temporary files.
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")

        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm.tobytes())
        return SpeechAudio(wav_buffer.getvalue())

    def close(self) -> None:
        """Release references to model weights and cached voice state."""
        self.voice_state = None
        self.model = None
