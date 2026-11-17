import os
import logging
import pygame
import screeninfo
from typing import Any

from hewo.main.endpoint import ServerEndPoint

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] - %(name)s: %(message)s")


class MainWindow:
    """Window manager that can host multiple *layouts* and cleans up audio/video gracefully."""

    def __init__(self, settings: dict[str, Any], layout_dict: dict[str, Any] | None = None,
                 active_layout: str | None = None):
        pygame.init()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings

        # ------------------------------------------------ monitor setup
        monitors = screeninfo.get_monitors()
        self.logger.info(f"Monitors detected → {[(m.name, m.width, m.height) for m in monitors]}")

        monitor_id = self.settings["monitor_id"]
        monitor_specs = monitors[monitor_id]

        flags = pygame.FULLSCREEN if self.settings["deploy"] else pygame.RESIZABLE
        self.window_size = (
            (monitor_specs.width, monitor_specs.height) if self.settings["deploy"] else (self.settings["width"],
                                                                                         self.settings["height"])
        )
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{monitor_specs.x},{monitor_specs.y}"

        self.logger.info(f"Window size = {self.window_size}")
        self.screen = pygame.display.set_mode(
            size=self.window_size,
            display=monitor_id,
            flags=flags,
            vsync=self.settings["vsync"],
        )
        pygame.display.set_caption(self.settings["window_title"])

        # ------------------------------------------------ layout handling
        self.layout_dict: dict[str, Any] = layout_dict or {}
        self.active_layout: str | None = active_layout
        self.background_color = tuple(self.settings["bg_color"])

        # ------------------------------------------------ misc state
        self.clock = pygame.time.Clock()
        self.fps = self.settings["fps"]

        # ------------------------------------------------ optional web endpoint
        if self.settings['enable_api']:
            self.web_server = ServerEndPoint(self)
            self.web_server.start()

    # ---------------------------------------------------------------- cleanup helpers
    def _shutdown_media(self):
        """Let each layout release resources it owns."""
        for layout in self.layout_dict.values():
            close = getattr(layout, "close", None)
            if callable(close):
                close()

    # ---------------------------------------------------------------- helpers
    def get_active_layout(self):
        return self.layout_dict.get(self.active_layout)

    # ---------------------------------------------------------------- event loop
    def handle_events(self):
        for event in pygame.event.get():
            resize_events = {pygame.VIDEORESIZE}
            if hasattr(pygame, "WINDOWRESIZED"):
                resize_events.add(pygame.WINDOWRESIZED)
            if hasattr(pygame, "WINDOWSIZECHANGED"):
                resize_events.add(pygame.WINDOWSIZECHANGED)
            if event.type in resize_events:
                previous_size = self.window_size
                # VIDEORESIZE uses w/h; SDL window events use x/y for the new
                # dimensions. Some fullscreen notifications carry neither.
                event_width = getattr(event, "w", getattr(event, "x", None))
                event_height = getattr(event, "h", getattr(event, "y", None))
                if event_width and event_height:
                    new_size = (event_width, event_height)
                else:
                    surface = pygame.display.get_surface()
                    new_size = surface.get_size() if surface is not None else self.screen.get_size()

                fullscreen = bool(self.settings["deploy"])
                if not fullscreen and self.screen.get_size() != new_size:
                    # Keep the window on whichever monitor the user moved it to.
                    # Passing the startup display index here snaps it back there.
                    position = None
                    try:
                        from pygame._sdl2.video import Window
                        position = Window.from_display_module().position
                    except Exception:
                        pass
                    self.screen = pygame.display.set_mode(
                        new_size, flags=pygame.RESIZABLE, vsync=self.settings["vsync"]
                    )
                    if position is not None:
                        try:
                            Window.from_display_module().position = position
                        except Exception:
                            pass
                elif fullscreen:
                    # The fullscreen display surface is managed by SDL; do not
                    # replace it with a windowed RESIZABLE surface on notification.
                    surface = pygame.display.get_surface()
                    if surface is not None:
                        self.screen = surface
                self.window_size = self.screen.get_size()
                self._sync_layout_boundaries()
                if self.window_size != previous_size:
                    layout = self.get_active_layout()
                    on_window_resized = getattr(layout, "on_window_resized", None)
                    if callable(on_window_resized):
                        on_window_resized(self.window_size)
            should_quit = event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            )
            if should_quit:
                self.logger.info("Shutting down…")
                self._shutdown_media()
                pygame.quit()
                raise SystemExit

            layout = self.get_active_layout()
            if layout:
                layout.handle_event(event)

    def _sync_layout_boundaries(self):
        if not hasattr(self, "screen"):
            return
        size = self.screen.get_size()
        self.window_size = size
        for layout in self.layout_dict.values():
            set_boundary = getattr(layout, "set_boundary", None)
            if callable(set_boundary):
                set_boundary(size)

    def set_active_layout(self, layout_key: str):
        if layout_key in self.layout_dict:
            self.active_layout = layout_key
            self.logger.info(f"Switched to layout → {layout_key}")
        else:
            self.logger.warning(f'Layout key "{layout_key}" not found; keeping current layout')

    # ---------------------------------------------------------------- update & draw
    def update(self, dt_ms: float):
        self._sync_layout_boundaries()
        layout = self.get_active_layout()
        if not layout:
            return
        layout.update(dt_ms)

    def draw(self):
        layout = self.get_active_layout()
        if layout is None or not getattr(layout, "clears_surface", False):
            self.screen.fill(self.background_color)
        if layout:
            layout.draw(self.screen)
        pygame.display.flip()

    # ---------------------------------------------------------------- main loop
    def run(self):
        while True:
            dt_ms = self.clock.tick(self.fps)
            self.handle_events()
            self.update(dt_ms)
            self.draw()
