import copy
import pygame
from hewo.objects.hewo.eye_components import EyeLash, Pupil
from hewo.settings import create_logger


class Eye:
    def __init__(self, size, position, settings, object_name="Eye"):
        self.logger = create_logger(object_name)
        self.settings = copy.deepcopy(settings)

        self.size = size
        self.position = position
        self.BG_COLOR = self.settings["bg_color"]

        # ---------------------------------------------------------------------
        # Component geometry
        # ---------------------------------------------------------------------
        self.lash_size = [self.size[0], self.size[1] / 2]
        self.t_pos = [0, 0]
        self.b_pos = [0, self.size[1] / 2]

        self.top_lash = EyeLash(
            size=self.lash_size,
            position=self.t_pos,
            settings=self.settings["top_lash"],
            object_name=f"{object_name} - Top Lash",
        )
        self.pupil = Pupil(
            size=self.size,
            position=self.position,
            settings=self.settings["pupil"],
            object_name=f"{object_name} - Pupil",
        )
        self.bot_lash = EyeLash(
            size=self.lash_size,
            position=self.b_pos,
            settings=self.settings["bot_lash"],
            object_name=f"{object_name} - Bottom Lash",
        )

        # ---------------------------------------------------------------------
        # Drawing surface: se crea UNA VEZ y se recrea sólo si cambia el tamaño
        # ---------------------------------------------------------------------
        self.eye_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        self._layout_dirty = False  # marca si hay que recrear la superficie

        # Blink state
        self.blinking = False
        self.blink_phase = 0
        self.original_top = self.top_lash.get_emotion()
        self.original_bot = self.bot_lash.get_emotion()
        self.logger.info(f"position: {self.position}")
        self.logger.info(f"size: {self.size}")

    # -------------------------------------------------------------------------
    # Event handling
    # -------------------------------------------------------------------------
    def handle_event(self, event):
        self.top_lash.handle_event(event)
        self.pupil.handle_event(event)
        self.bot_lash.handle_event(event)

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------
    def draw(self, surface):
        # Sólo recreamos la surface si el tamaño cambió
        if self._layout_dirty:
            self.eye_surface = pygame.Surface(self.size)
            self._layout_dirty = False

        self.eye_surface.fill(self.BG_COLOR)

        self.pupil.draw(self.eye_surface)
        self.top_lash.draw(self.eye_surface)
        self.bot_lash.draw(self.eye_surface)

        surface.blit(self.eye_surface, self.position)

    # -------------------------------------------------------------------------
    # Logic / update
    # -------------------------------------------------------------------------
    def update(self):
        self.top_lash.update()
        self.pupil.update()
        self.bot_lash.update()
    # -------------------------------------------------------------------------
    # Blink animation
    # -------------------------------------------------------------------------
    def trigger_blink(self):
        if not self.blinking:
            self.blinking = True
            self.blink_phase = 0
            self.original_top = self.top_lash.get_emotion()
            self.original_bot = self.bot_lash.get_emotion()

    def animate_blink(self, closing_frames=23, opening_frames=2):
        total_phases = closing_frames + opening_frames

        if self.blinking:
            phase = self.blink_phase

            if phase < closing_frames:
                # Fase de cierre
                t = phase / closing_frames
                interp_top = [int((1 - t) * o + t * 100) for o in self.original_top]
                interp_bot = [int((1 - t) * o + t * 100) for o in self.original_bot]
            else:
                # Fase de apertura
                t = (phase - closing_frames) / opening_frames
                interp_top = [int((1 - t) * 100 + t * o) for o in self.original_top]
                interp_bot = [int((1 - t) * 100 + t * o) for o in self.original_bot]

            self.top_lash.set_emotion(interp_top)
            self.bot_lash.set_emotion(interp_bot)

            self.blink_phase += 1
            if self.blink_phase >= total_phases:
                self.blinking = False
                self.top_lash.set_emotion(self.original_top)
                self.bot_lash.set_emotion(self.original_bot)

    # -------------------------------------------------------------------------
    # Emotion helpers
    # -------------------------------------------------------------------------
    def set_emotion(self, t_emotion, p_emotion, b_emotion):
        self.top_lash.set_emotion(t_emotion)
        self.bot_lash.set_emotion(b_emotion)
        self.pupil.set_emotion(p_emotion)

    def get_emotion(self):
        top_emotion = self.top_lash.get_emotion()
        bot_emotion = self.bot_lash.get_emotion()
        pupil_emotion = self.pupil.get_emotion()
        return top_emotion, pupil_emotion, bot_emotion

    # -------------------------------------------------------------------------
    # Geometry setters
    # -------------------------------------------------------------------------
    def set_size(self, size):
        if size != self.size:
            self.size = size
            self.lash_size = [self.size[0], self.size[1] / 2]
            self.top_lash.set_size(self.lash_size)
            self.bot_lash.set_size(self.lash_size)
            self.pupil.size = self.size
            self._layout_dirty = True
            # reseteo de blink para evitar parpadeo roto tras resize
            self.blinking = False
            self.blink_phase = 0

    def set_position(self, position):
        self.position = position
        self.t_pos = [0, 0]
        self.b_pos = [0, self.size[1] / 2]
        self.top_lash.set_position(self.t_pos)
        self.bot_lash.set_position(self.b_pos)
        self.pupil.position = position
