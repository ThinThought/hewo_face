import pygame
import random
from hewo.objects.hewo.face import Face
from hewo.settings import SettingsLoader, create_logger
from hewo.objects.hewo.logic.emotion_mapper import EmotionMapper
from hewo.objects.hewo.logic.input_handler import HeWoInputHandler


class HeWo(Face):
    def __init__(self, settings, object_name="HeWo"):
        super().__init__(settings=settings)
        self.logger = create_logger(object_name)
        self.settings = settings

        self.mapper = EmotionMapper()
        self.input_handler = HeWoInputHandler(self, self.mapper)

    def set_emotion_goal(self, emotion_goal):
        self.logger.debug(f"Setting emotion goal: {emotion_goal}")
        self.mapper.emotion_goal = emotion_goal
        self.update_face()

    def get_emotion(self):
        return self.mapper.get_emotion(self)

    def update(self):
        if self.input_handler.manual_mode:
            self.input_handler.handle_keypressed()
        self.mapper.update_emotion(self)
        self.update_face()

    def handle_event(self, event):
        if self.input_handler.manual_mode:
            self.input_handler.handle_event(event)

    def toggle_talk(self):
        self.mouth.toggle_talk()

    def trigger_blink(self):
        self.left_eye.trigger_blink()
        self.right_eye.trigger_blink()

    def adjust_position(self, dx, dy):
        pos = self.position
        pos[0] += dx
        pos[1] += dy
        self.set_position(pos)

    def set_face_size(self, new_size):
        self.set_size(new_size)
        self.adjust_position(0, 0)

    def set_random_emotion(self):
        self.mapper.set_random_emotion()

    def reset_emotion(self):
        self.mapper.reset_emotion()

    def adjust_emotion(self, param, value):
        """Set emotion parameter `param` to a specific `value` (0-100 clamped)."""
        clamped_value = max(0, min(100, value))
        self.mapper.emotion_goal[param] = clamped_value
        self.logger.debug(f"Set {param} to {clamped_value}")


# Código de prueba
def test_component():
    pygame.init()
    settings = SettingsLoader().load_settings("game.settings.hewo")
    hewo = HeWo(settings=settings)

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("HeWo Class")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            hewo.handle_event(event)
        hewo.update()
        screen.fill((255, 255, 255))
        hewo.draw(screen)
        pygame.display.flip()
    pygame.quit()


if __name__ == '__main__':
    test_component()
