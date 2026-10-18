import pygame

class HeWoInputHandler:
    def __init__(self, hewo, mapper, move_step=10):
        self.hewo = hewo
        self.mapper = mapper
        self.move_step = move_step
        self.increase_mode = True
        self.manual_mode = True

        self.key_down_mappings = {
            pygame.K_SPACE: self.toggle_mode,
            pygame.K_1: self.toggle_talk,
            pygame.K_2: self.trigger_blink
        }

        self.key_pressed_mappings = {
            pygame.K_m: self.mapper.set_random_emotion,
            pygame.K_n: self.mapper.reset_emotion,
            pygame.K_v: lambda: self.adjust_size(self.move_step),
            pygame.K_b: lambda: self.adjust_size(-self.move_step),
            pygame.K_UP: lambda: self.adjust_position(0, -self.move_step),
            pygame.K_DOWN: lambda: self.adjust_position(0, self.move_step),
            pygame.K_LEFT: lambda: self.adjust_position(-self.move_step, 0),
            pygame.K_RIGHT: lambda: self.adjust_position(self.move_step, 0),
        }

        self.map_emotion_keys()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in self.key_down_mappings:
                self.key_down_mappings[event.key]()

    def handle_keypressed(self):
        keys = pygame.key.get_pressed()
        for key, action in self.key_pressed_mappings.items():
            if keys[key]:
                action()

    def map_emotion_keys(self):
        keys = [
            pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y,
            pygame.K_u, pygame.K_i, pygame.K_o, pygame.K_p, pygame.K_a, pygame.K_s,
            pygame.K_d, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_j, pygame.K_k,
            pygame.K_l, pygame.K_z, pygame.K_x, pygame.K_c
        ]
        parameters = list(self.mapper.emotion_goal.keys())

        for key, param in zip(keys, parameters):
            self.key_pressed_mappings[key] = lambda p=param: self.adjust_emotion(p)

    def toggle_mode(self):
        self.increase_mode = not self.increase_mode
        mode = "Increase" if self.increase_mode else "Decrease"
        self.hewo.logger.debug(f"Mode toggled to: {mode}")

    def adjust_emotion(self, param):
        if self.increase_mode:
            self.mapper.emotion_goal[param] = min(100, self.mapper.emotion_goal[param] + self.mapper.emotion_step)
        else:
            self.mapper.emotion_goal[param] = max(0, self.mapper.emotion_goal[param] - self.mapper.emotion_step)
        self.hewo.logger.debug(f"Adjusted {param} to {self.mapper.emotion_goal[param]}")

    def adjust_position(self, dx, dy):
        position = self.hewo.position
        position[0] += dx
        position[1] += dy
        self.hewo.set_position(position)
        self.hewo.logger.debug(f"Position adjusted to: {position}")

    def adjust_size(self, ds):
        size_factor = self.hewo.size_factor
        size_factor += ds
        self.hewo.set_size(size_factor)
        self.adjust_position(0, 0)

    def toggle_talk(self):
        self.hewo.mouth.toggle_talk()
        if self.hewo.mouth.is_talking:
            self.hewo.logger.debug("Talking mode activated.")
        else:
            self.hewo.logger.debug("Talking mode deactivated.")

    def trigger_blink(self):
        self.hewo.left_eye.trigger_blink()
        self.hewo.right_eye.trigger_blink()
        self.hewo.logger.debug("Blink triggered.")
