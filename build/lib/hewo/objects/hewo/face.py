import pygame
import copy
import random
from hewo.objects.hewo.eye import Eye
from hewo.objects.hewo.mouth import Mouth
from hewo.settings import SettingsLoader, create_logger

PHI = (1 + 5 ** 0.5) / 2  # proporción áurea


class Face:
    def __init__(self, settings=None, object_name="Face"):
        self.settings = copy.deepcopy(settings)
        self.logger = create_logger(object_name)

        # -------------------------------------------------- tamaño / posición
        self.size_factor = self.settings["face"]["size"]
        self.min_size_factor = self.settings["face"]["min_size"]
        self.max_size_factor = self.settings["face"]["max_size"]
        self.size = [int(PHI * self.size_factor), int(self.size_factor)]
        self.position = self.settings["face"]["position"]
        self.boundary = self.settings["face"]["boundary"]

        # -------------------------------------------------- superficie persistente
        self.color = tuple(self.settings["face"]["bg_color"])
        self.face_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        self._layout_dirty = False

        # -------------------------------------------------- crear ojos y boca
        self._refresh_child_sizes_positions()

        self.left_eye = Eye(
            self.eye_size,
            self.left_eye_pos,
            settings=copy.deepcopy(self.settings["eye"]),
            object_name="Left Eye",
        )
        self.right_eye = Eye(
            self.eye_size,
            self.right_eye_pos,
            settings=copy.deepcopy(self.settings["eye"]),
            object_name="Right Eye",
        )
        self.mouth = Mouth(
            self.mouth_size,
            self.mouth_pos,
            settings=copy.deepcopy(self.settings["mouth"]),
            object_name="Mouth",
        )
        # -------------------------------------------------- blink
        self.blink_timer = 0
        self.blink_interval = random.randint(300, 700)

    # ------------------------------------------------------------------ layout helper
    def _refresh_child_sizes_positions(self):
        """Calcula eye_size, mouth_size y sus posiciones como enteros."""
        self.eye_size = [int(self.size[0] / 5), int(self.size[1] * 4 / 5)]
        self.mouth_size = [int(self.size[0] * 3 / 5), int(self.size[1] / 5)]

        self.left_eye_pos = [0, 0]
        self.right_eye_pos = [int(self.eye_size[0] * 4), 0]
        self.mouth_pos = [int(self.eye_size[0]), int(self.eye_size[1])]

    def _update_layout(self):
        """Recalcula tamaños y posiciones internas cuando _layout_dirty."""
        self.face_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        self._refresh_child_sizes_positions()

        self.left_eye.set_size(self.eye_size)
        self.right_eye.set_size(self.eye_size)
        self.mouth.set_size(self.mouth_size)

        self.left_eye.set_position(self.left_eye_pos)
        self.right_eye.set_position(self.right_eye_pos)
        self.mouth.set_position(self.mouth_pos)

        self._layout_dirty = False

    # ------------------------------------------------------------------ setters públicos
    def set_size(self, size_factor):
        if self.min_size_factor <= size_factor <= self.max_size_factor:
            self.size_factor = size_factor
            self.size = [int(PHI * size_factor), int(size_factor)]
            self._layout_dirty = True


    def set_position(self, pos):
        self.position[0] = max(0, min(pos[0], self.boundary[0] - self.size[0]))
        self.position[1] = max(0, min(pos[1], self.boundary[1] - self.size[1]))

    # ------------------------------------------------------------------ núcleo de actualización
    def _core_update(self):
        # parpadeo aleatorio
        self.blink_timer += 1
        if self.blink_timer >= self.blink_interval:
            self.left_eye.trigger_blink()
            self.right_eye.trigger_blink()
            self.blink_timer = 0
            self.blink_interval = random.randint(300, 700)

        # relayout si es necesario
        if self._layout_dirty:
            self._update_layout()

        # animaciones y lógica interna
        self.left_eye.animate_blink()
        self.right_eye.animate_blink()

        self.left_eye.update()
        self.right_eye.update()
        self.mouth.update()

    # ------------------------------------------------------------------ API pública
    def update(self):
        self._core_update()

    def update_face(self):
        self._core_update()

    def handle_event(self, event):
        self.left_eye.handle_event(event)
        self.right_eye.handle_event(event)
        self.mouth.handle_event(event)

    def draw(self, surface):
        if self._layout_dirty:
            self._update_layout()

        self.face_surface.fill(self.color)
        self.left_eye.draw(self.face_surface)
        self.right_eye.draw(self.face_surface)
        self.mouth.draw(self.face_surface)
        surface.blit(self.face_surface, dest=self.position)


# --------------------------------------------------------------------------- prueba rápida
if __name__ == "__main__":
    pygame.init()
    settings = SettingsLoader().load_settings("game.settings.hewo")
    screen = pygame.display.set_mode((800, 600))
    face = Face(settings=settings)
    clock = pygame.time.Clock()
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            face.handle_event(ev)

        face.update()
        screen.fill((255, 255, 255))
        face.draw(screen)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()
