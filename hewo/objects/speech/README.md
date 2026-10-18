# Speech module

This package keeps text-to-speech engines separate from Pygame playback and
face animation. Engines implement `SpeechEngine` and return WAV bytes as
`SpeechAudio`; `SpeechController` runs synthesis and playback on a worker
thread, then sends lifecycle events back to the application's update loop.

## Try Pocket TTS

Install the optional dependency with `uv sync --extra speech`. The first
initialization downloads and caches the model and voice data; later starts can
reuse that cache. Pocket TTS is an open-source local model that runs on CPU.
Its int8 quantization option can reduce memory use and may improve speed on
CPU-only devices; benchmark it on the target Raspberry Pi because performance
depends on the board and model.

From the project root, generate and play a test phrase with:

```bash
uv run --extra speech python scripts/test_speech.py --language spanish --voice lola
```

Use `--save speech-sample.wav` to keep a copy, `--no-play` to only synthesize,
or `--text "Tu frase de prueba"` to change the phrase. Omit `--voice` to use
Pocket TTS's default for the selected language.

```python
from hewo.objects.hewo import HeWo
from hewo.objects.speech import SpeechController
from hewo.objects.speech.backends.pocket_tts import PocketTTSEngine
from hewo.objects.speech.output import PygameAudioOutput

speech = SpeechController(
    PocketTTSEngine(language="spanish", voice="lola", quantize=True),
    PygameAudioOutput(),
)
hewo = HeWo(settings=hewo_settings, speech_controller=speech)
hewo.say("Hola, estoy hablando")
```

`voice` accepts a built-in voice name or an audio prompt path/URL (including
`hf://` references) for voice cloning. If omitted, this adapter selects the
documented default for the selected language. `quantize=True` is intended for
CPU execution.

### Built-in voices

The voice names below can be passed as `voice="name"` to `PocketTTSEngine` or
to `scripts/test_speech.py --voice name`:

| Language | Voices |
| --- | --- |
| English (`en`) | `alba`, `anna`, `azelma`, `bill_boerst`, `caro_davy`, `charles`, `cosette`, `eponine`, `eve`, `fantine`, `george`, `jane`, `javert`, `jean`, `marius`, `mary`, `michael`, `paul`, `peter_yearsley`, `stuart_bell`, `vera` |
| Spanish (`es`) | `lola` |
| French (`fr`) | `estelle` |
| German (`de`) | `juergen` |
| Italian (`it`) | `giovanni` |
| Portuguese (`pt`) | `rafael` |

Pocket TTS also provides language-specific default voices; leaving `voice`
unset lets the installed engine version select one. The preset list is not
exhaustive: the [Kyutai voice repository](https://huggingface.co/kyutai/tts-voices)
contains additional audio prompts that can be selected by URL or downloaded
and used by local path.

### Language models

Current model identifiers include:

- English: `english`, `english_2026-01`, `english_2026-04`,
  `english_2026-09`, `english_2026-09_2`, `english_drifting_26-09`.
- Spanish, French, German, Italian, Portuguese, and Dutch: the language name
  (for example, `spanish` or `dutch`). Preview variants with the `_24l` suffix
  are available for these languages; they are larger, undistilled models and
  may be slower on a Raspberry Pi.

Set `language` when constructing `PocketTTSEngine`, for example
`PocketTTSEngine(language="spanish", voice="lola")`. A voice prompt can also
be a local WAV/audio file or a Hugging Face URL such as
`hf://kyutai/tts-voices/alba-mackenna/casual.wav`. Choose a prompt spoken in
the target language for the most suitable accent. Pocket TTS extracts and
caches the voice conditioning state when the engine is constructed, so voice
preparation does not repeat for every utterance.

### Speech and mouth animation lifecycle

`SpeechController` calls synthesis on its worker thread. Once the full utterance
has been synthesized, it emits `STARTED` immediately before audio playback and
`FINISHED` after playback ends. `HeWo.update()` consumes these events and calls
`Mouth.set_talking(True/False)`, so the mouth animation follows audible
playback rather than model inference. If synthesis or playback fails, the
controller emits `FAILED` and the mouth animation is stopped. The current HeWo
adapter does not consume Pocket TTS's streaming chunks; adding streaming would
allow playback and animation to start earlier for long utterances.

Call `hewo.close()` when shutting down to stop playback and release the model
and voice state. The main application still leaves the speech controller
unconfigured by default; selecting an engine in the composition root remains
an explicit integration step.

### Pocket TTS references

- [Kyutai Pocket TTS source repository](https://github.com/kyutai-labs/pocket-tts)
- [Python API: model loading, voice prompts, and audio generation](https://github.com/kyutai-labs/pocket-tts/blob/main/docs/API%20Reference/python-api.md)
- [Built-in voice names in the official UI](https://github.com/kyutai-labs/pocket-tts/blob/main/pocket_tts/static/index.html)
- [Official voice prompt repository](https://huggingface.co/kyutai/tts-voices)
- [Model versions and release notes](https://github.com/kyutai-labs/pocket-tts/releases)

## Try the eSpeak NG adapter

Install eSpeak NG on the system and make sure `espeak-ng` is available on
`PATH`. It is an optional system executable, so the face application does not
require it just to start.

```python
from hewo.objects.hewo import HeWo
from hewo.objects.speech import SpeechController
from hewo.objects.speech.backends.espeak_ng import EspeakNgEngine
from hewo.objects.speech.output import PygameAudioOutput

speech = SpeechController(EspeakNgEngine(voice="es"), PygameAudioOutput())
hewo = HeWo(settings=hewo_settings, speech_controller=speech)
hewo.say("Hola, estoy hablando")
```

Call `hewo.update()` regularly while speech is playing so it can consume
controller events and start/stop the existing mouth animation.

## Add another engine

Implement `SpeechEngine.synthesize(text)` and `SpeechEngine.close()`. Keep
engine-specific model loading and inference in that adapter. Return WAV audio
in `SpeechAudio`; playback, queueing, and mouth animation remain in the shared
controller. This allows local options such as Piper to be compared without
coupling them to `HeWo`.
