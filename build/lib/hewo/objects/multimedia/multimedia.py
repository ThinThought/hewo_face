import os
import shutil
import subprocess
import pygame
import cv2
from hewo.settings import create_logger


class Multimedia:
    """Image/video handler with optional audio. Provides update & draw hooks."""

    SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif"}
    SUPPORTED_VIDEO_EXTS = {".mp4", ".mov"}

    def __init__(
        self,
        filepath: str,
        loop: bool = True,
        audio: bool = False,
        *,
        target_size: tuple[int, int] | None = None,
        object_name: str = "Multimedia",
    ):
        self.logger = create_logger(object_name)
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)

        self.filepath = filepath
        self.loop = loop
        self.audio_enabled = audio
        self.target_size = target_size

        self.audio_mode: str | None = None
        self.audio_proc: subprocess.Popen | None = None

        self.is_playing = False
        self.finished = False

        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        if ext in self.SUPPORTED_IMAGE_EXTS:
            self.media_type = "image"
            self._load_image(filepath)
        elif ext in self.SUPPORTED_VIDEO_EXTS:
            self.media_type = "video"
            self._load_video(filepath)
        else:
            raise ValueError(f"Unsupported media extension: {ext}")

    def _setup_audio(self):
        if not self.audio_enabled or self.media_type != "video":
            return

        if shutil.which("ffplay") is None:
            self.logger.warning("ffplay not found in PATH – audio disabled")
            self.audio_mode = None
            return

        self.audio_mode = "ffplay"

        if self.is_playing:
            self._start_audio()

    def _start_audio(self):
        if self.audio_mode == "ffplay":
            args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            if self.loop:
                args += ["-loop", "0"]
            args.append(self.filepath)
            self.audio_proc = subprocess.Popen(args)

    def _stop_audio(self):
        if self.audio_mode == "ffplay" and self.audio_proc is not None:
            self.audio_proc.kill()
            self.audio_proc = None

    def _apply_target_size(self):
        if self.target_size and self.surface.get_size() != self.target_size:
            self.surface = pygame.transform.smoothscale(self.surface, self.target_size)
            self.rect = self.surface.get_rect(topleft=self.rect.topleft)

    def _load_image(self, path):
        self.surface = pygame.image.load(path).convert_alpha()
        self.rect = self.surface.get_rect()
        self._apply_target_size()
        self.original_surface = self.surface.copy()
        self.logger.info(f"Loaded image {path} size={self.rect.size}")

    def _load_video(self, path):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video {path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_interval = 1000 / self.fps
        success, frame = self.cap.read()
        if not success:
            raise RuntimeError("Could not read first frame")
        self._frame_to_surface(frame)
        self.timer = 0.0
        self._setup_audio()
        self.logger.info(f"Loaded video {path} fps={self.fps:.1f}")

    def _frame_to_surface(self, frame):
        prev_pos = getattr(self, "rect", pygame.Rect(0, 0, 0, 0)).topleft
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        h, w = frame.shape[:2]
        surface = pygame.image.frombuffer(frame.tobytes(), (w, h), "RGBA")
        self.surface = surface.convert_alpha()
        self.rect = self.surface.get_rect(topleft=prev_pos)
        self._apply_target_size()
        self.original_surface = self.surface.copy()

    def update(self, dt_ms: float):
        if self.media_type == "image" or not self.is_playing or self.finished:
            return

        self.timer += dt_ms
        while self.timer >= self.frame_interval:
            self.timer -= self.frame_interval
            success, frame = self.cap.read()
            if not success:
                if self.loop:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = self.cap.read()
                    if not success:
                        self.finished = True
                        break
                else:
                    self.finished = True
                    break
            if success:
                self._frame_to_surface(frame)

        if self.finished and not self.loop:
            self._stop_audio()

    def draw(self, target_surface: pygame.Surface, position):
        if not self.finished:
            target_surface.blit(self.surface, position)

    def play(self):
        if self.finished:
            self.stop()
        self.is_playing = True
        if self.audio_mode == "ffplay" and self.audio_proc is None:
            self._start_audio()

    def pause(self):
        self.is_playing = False
        if self.audio_mode == "ffplay":
            self._stop_audio()

    def stop(self):
        self.is_playing = False
        if self.media_type == "video":
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.timer = 0.0
            self.finished = False
        self._stop_audio()

    def __del__(self):
        self._stop_audio()


class MultimediaGameObj(Multimedia):
    def __init__(
        self,
        filepath: str,
        position=(0, 0),
        velocity=(0, 0),
        *,
        size: tuple[int, int] | None = None,
        loop: bool = True,
        audio: bool = False,
        object_name: str = "MultimediaObj",
        autoplay: bool = False,
    ):
        self.rect = pygame.Rect(position, (0, 0))
        super().__init__(filepath, loop=loop, audio=audio, target_size=size, object_name=object_name)
        if autoplay:
            self.play()
        self.rect.topleft = position
        self.velocity = pygame.Vector2(velocity)

    def handle_event(self, event):
        pass

    def update(self, dt_ms: float):
        super().update(dt_ms)
        self.rect.x += self.velocity.x * dt_ms / 1000.0
        self.rect.y += self.velocity.y * dt_ms / 1000.0

    def draw(self, target_surface: pygame.Surface):
        super().draw(target_surface, self.rect.topleft)


class MultimediaLayout:
    def __init__(self, settings):
        self.logger = create_logger(settings['object_name'])
        self.bg_color = settings['bg_color']
        self.objects = []
        self.object_description = settings['objects']
        for obj in self.object_description:
            obj = MultimediaGameObj(**obj) if isinstance(obj, dict) else obj
            self.objects.append(obj)

    def add_object(self, obj: MultimediaGameObj):
        self.objects.append(obj)

    def remove_object(self, obj: MultimediaGameObj):
        if obj in self.objects:
            self.objects.remove(obj)
            obj.stop()

    def handle_event(self, event):
        for obj in self.objects:
            obj.handle_event(event)

    def update(self, dt_ms: float):
        for obj in self.objects:
            obj.update(dt_ms)

    def draw(self, surface: pygame.Surface):
        surface.fill(self.bg_color)
        for obj in self.objects:
            obj.draw(surface)

    def get_object_by_name(self, name: str) -> MultimediaGameObj | None:
        for obj in self.objects:
            if getattr(obj, 'logger', None) and obj.logger.name == name:
                return obj
            if getattr(obj, 'object_name', '') == name:
                return obj
        return None

    def move_object(self, name: str, dx: int, dy: int):
        obj = self.get_object_by_name(name)
        if obj:
            obj.rect.x += dx
            obj.rect.y += dy
            self.logger.info(f"Moved '{name}' by ({dx}, {dy})")

    def set_position(self, name: str, x: int, y: int):
        obj = self.get_object_by_name(name)
        if obj:
            obj.rect.topleft = (x, y)
            self.logger.info(f"Set position of '{name}' to ({x}, {y})")

    def pause_object(self, name: str):
        obj = self.get_object_by_name(name)
        if obj:
            obj.pause()
            self.logger.info(f"Paused '{name}'")

    def play_object(self, name: str):
        obj = self.get_object_by_name(name)
        if obj:
            obj.play()
            self.logger.info(f"Played '{name}'")

    def remove_by_name(self, name: str):
        obj = self.get_object_by_name(name)
        if obj:
            self.remove_object(obj)
            self.logger.info(f"Removed '{name}'")
