"""Asynchronous speech queue that reports lifecycle events to the app loop."""

from queue import Empty, Queue, SimpleQueue
from threading import Lock, Thread

from hewo.objects.speech.engine import SpeechAudio, SpeechEngine
from hewo.objects.speech.events import SpeechEvent, SpeechEventKind
from hewo.objects.speech.output import AudioOutput


class SpeechController:
    """Runs synthesis and playback outside Pygame's frame-update thread.

    Engines and outputs are injected so Piper, eSpeak, Pocket TTS, and future
    backends can be compared without changing face or animation code.
    """

    def __init__(self, engine: SpeechEngine, output: AudioOutput):
        self.engine = engine
        self.output = output
        self._requests = Queue()
        self._events = SimpleQueue()
        self._lock = Lock()
        self._closed = False
        self._worker = Thread(target=self._run, name="hewo-speech", daemon=True)
        self._worker.start()

    def speak(self, text: str) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Speech text must be a non-empty string")
        with self._lock:
            if self._closed:
                raise RuntimeError("SpeechController is closed")
            self._requests.put(text.strip())

    def drain_events(self) -> list[SpeechEvent]:
        """Return pending events; call this from the Pygame update thread."""
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except Empty:
                return events

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            while True:
                try:
                    self._requests.get_nowait()
                except Empty:
                    break
            self._requests.put(None)

        self.output.stop()
        self._worker.join(timeout=1.0)

    def _run(self) -> None:
        while True:
            text = self._requests.get()
            if text is None:
                break

            try:
                audio = self.engine.synthesize(text)
                if not isinstance(audio, SpeechAudio):
                    raise TypeError("SpeechEngine.synthesize must return SpeechAudio")
                self._events.put(SpeechEvent(SpeechEventKind.STARTED, text))
                self.output.play(audio)
                self._events.put(SpeechEvent(SpeechEventKind.FINISHED, text))
            except Exception as error:
                self._events.put(
                    SpeechEvent(SpeechEventKind.FAILED, text, str(error))
                )

        self.output.close()
        self.engine.close()
