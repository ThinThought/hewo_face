"""Generate and optionally play a sample with the configured speech engine."""

import argparse
from pathlib import Path
import time

import pygame

from hewo.objects.speech.backends.pocket_tts import PocketTTSEngine
from hewo.objects.speech.output import PygameAudioOutput


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="Prueba de voz", help="Text to synthesize")
    parser.add_argument("--language", default="spanish")
    parser.add_argument("--voice", help="Voice preset or audio prompt path/URL")
    parser.add_argument("--quantize", action="store_true", help="Use CPU int8 quantization")
    parser.add_argument("--save", type=Path, help="Also save the generated WAV to this path")
    parser.add_argument("--no-play", action="store_true", help="Generate audio without playback")
    args = parser.parse_args()

    engine = None
    try:
        print(f"Loading Pocket TTS ({args.language}, voice={args.voice or 'default'})...")
        started_at = time.perf_counter()
        engine = PocketTTSEngine(
            language=args.language,
            voice=args.voice,
            quantize=args.quantize,
        )
        print(f"Model and voice loaded in {time.perf_counter() - started_at:.2f}s")

        print("Synthesizing...")
        started_at = time.perf_counter()
        audio = engine.synthesize(args.text)
        print(f"Generated {len(audio.wav_data):,} WAV bytes in {time.perf_counter() - started_at:.2f}s")

        if args.save:
            args.save.write_bytes(audio.wav_data)
            print(f"Saved audio to {args.save}")

        if not args.no_play:
            pygame.mixer.init()
            print("Playing speech...")
            PygameAudioOutput().play(audio)
            print("Playback finished.")
    except Exception as error:
        parser.exit(1, f"Speech test failed: {error}\n")
    finally:
        if engine is not None:
            engine.close()
        if pygame.mixer.get_init():
            pygame.mixer.quit()


if __name__ == "__main__":
    main()
