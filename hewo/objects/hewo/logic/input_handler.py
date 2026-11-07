import pygame
from pygame._sdl2 import controller as sdl_controller

class HeWoInputHandler:
    def __init__(self, hewo, mapper, move_step=10):
        self.hewo = hewo
        self.mapper = mapper
        self.move_step = move_step
        self.increase_mode = True
        self.manual_mode = True
        self.gamepad = None
        self._button_states = {
            pygame.CONTROLLER_BUTTON_A: False,
            pygame.CONTROLLER_BUTTON_B: False,
        }
        self.deadzone = float(self.hewo.spherical.get("deadzone", 0.16))
        self._init_controller()

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
        if (self.hewo.spherical_enabled
                and event.type == pygame.CONTROLLERDEVICEADDED
                and self.gamepad is None):
            self._open_controller(event.device_index)
        elif event.type == pygame.CONTROLLERDEVICEREMOVED and self.gamepad is not None:
            if self.gamepad.as_joystick().get_instance_id() == event.instance_id:
                self.gamepad.quit()
                self.gamepad = None
                self._reset_button_states()
        elif self.manual_mode and event.type == pygame.KEYDOWN:
            if event.key in self.key_down_mappings:
                self.key_down_mappings[event.key]()

    def _init_controller(self):
        if not self.hewo.spherical_enabled:
            return
        pygame.joystick.init()
        sdl_controller.init()
        for device_index in range(pygame.joystick.get_count()):
            if self._open_controller(device_index):
                break

    def _open_controller(self, device_index):
        if not sdl_controller.is_controller(device_index):
            return False
        self.gamepad = sdl_controller.Controller(device_index)
        self.gamepad.init()
        self.hewo.logger.info("Joystick conectado: %s", self.gamepad.name)
        return True

    def _axis(self, axis):
        value = max(-1.0, min(1.0, self.gamepad.get_axis(axis) / 32767.0))
        magnitude = abs(value)
        if magnitude <= self.deadzone:
            return 0.0
        return (1 if value > 0 else -1) * (magnitude - self.deadzone) / (1.0 - self.deadzone)

    def update(self, dt_ms):
        if self.gamepad is None or not self.gamepad.attached():
            return
        sdl_controller.update()
        dt_seconds = max(0.0, min(float(dt_ms or 0) / 1000.0, 0.05))

        if self._button_just_pressed(pygame.CONTROLLER_BUTTON_A):
            self.hewo.trigger_blink()
        if self._button_just_pressed(pygame.CONTROLLER_BUTTON_B):
            self.hewo.toggle_talk()

        left_x = self._axis(pygame.CONTROLLER_AXIS_LEFTX)
        left_y = -self._axis(pygame.CONTROLLER_AXIS_LEFTY)
        self.hewo.move_on_sphere(left_x, left_y, dt_seconds)

        right_x = self._axis(pygame.CONTROLLER_AXIS_RIGHTX)
        right_y = self._axis(pygame.CONTROLLER_AXIS_RIGHTY)
        xy_speed = float(self.hewo.spherical.get("xy_translation_speed", 220.0))
        if right_x or right_y:
            self.hewo.adjust_position(right_x * xy_speed * dt_seconds,
                                      right_y * xy_speed * dt_seconds)

        left_bumper = self.gamepad.get_button(pygame.CONTROLLER_BUTTON_LEFTSHOULDER)
        right_bumper = self.gamepad.get_button(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER)
        depth_direction = right_bumper - left_bumper
        if depth_direction:
            self.hewo.move_camera_depth(depth_direction, dt_seconds)

        left_trigger = max(0.0, self._axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT))
        right_trigger = max(0.0, self._axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT))
        self.hewo.rotate_on_sphere(right_trigger - left_trigger, dt_seconds)

    def _button_just_pressed(self, button):
        is_pressed = bool(self.gamepad.get_button(button))
        was_pressed = self._button_states[button]
        self._button_states[button] = is_pressed
        return is_pressed and not was_pressed

    def _reset_button_states(self):
        for button in self._button_states:
            self._button_states[button] = False

    def close(self):
        if self.gamepad is not None:
            self.gamepad.quit()
            self.gamepad = None
        self._reset_button_states()

    def handle_keypressed(self):
        if not self.manual_mode:
            return
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
        parameters = self.mapper.keys

        for key, param in zip(keys, parameters):
            self.key_pressed_mappings[key] = lambda p=param: self.adjust_emotion(p)

    def toggle_mode(self):
        self.increase_mode = not self.increase_mode
        mode = "Increase" if self.increase_mode else "Decrease"
        self.hewo.logger.debug(f"Mode toggled to: {mode}")

    def adjust_emotion(self, param):
        delta = self.mapper.emotion_step if self.increase_mode else -self.mapper.emotion_step
        value = self.mapper.adjust_goal(param, delta)
        self.hewo.logger.debug(f"Adjusted {param} to {value}")

    def adjust_position(self, dx, dy):
        self.hewo.adjust_position(dx, dy)
        self.hewo.logger.debug(f"Position adjusted to: {self.hewo.position}")

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
