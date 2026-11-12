import pygame
import copy
import random
import math
import threading
from numbers import Real
import cv2
import numpy as np
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
        self.boundary_margin = float(self.settings["face"].get("boundary_margin", 0))
        self.spherical = copy.deepcopy(self.settings["face"].get("spherical", {}))
        self.spherical_enabled = self.spherical.get("enabled", True)
        self.sphere_radius = float(self.spherical.get("radius", 190.0))
        self.camera_distance = float(self.spherical.get("camera_distance", 720.0))
        self.focal_length = float(self.spherical.get("focal_length", 720.0))
        self.sphere_normal = (0.0, 0.0, -1.0)
        # These reference axes define a repeatable orientation at every point
        # on the sphere, avoiding accumulated twist along closed joystick paths.
        self.sphere_reference_right = (1.0, 0.0, 0.0)
        self.sphere_reference_up = (0.0, 1.0, 0.0)
        self.sphere_roll = 0.0
        self._pose_lock = threading.RLock()
        self._position_goals = {
            "x": float(self.position[0]),
            "y": float(self.position[1]),
            "z": self.camera_distance,
        }
        self._position_speeds = {axis: None for axis in self._position_goals}
        self._surface_goals = {"longitude": 0.0, "latitude": 0.0, "roll": 0.0}
        self._surface_speeds = {axis: None for axis in self._surface_goals}

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
            with self._pose_lock:
                self.size_factor = size_factor
                self.size = [int(PHI * size_factor), int(size_factor)]
                self._layout_dirty = True
                self.set_boundary(self.boundary)


    def set_position(self, pos):
        with self._pose_lock:
            self.position[0] = max(0, min(pos[0], self.boundary[0] - self.size[0] - self.boundary_margin))
            self.position[1] = max(0, min(pos[1], self.boundary[1] - self.size[1] - self.boundary_margin))

    def set_boundary(self, boundary):
        """Update available render area and keep current and queued XY inside it."""
        width, height = (max(0.0, float(value)) for value in boundary)
        with self._pose_lock:
            self.boundary = [width, height]
            max_x = max(0.0, width - self.size[0] - self.boundary_margin)
            max_y = max(0.0, height - self.size[1] - self.boundary_margin)
            self.position[0] = max(0.0, min(float(self.position[0]), max_x))
            self.position[1] = max(0.0, min(float(self.position[1]), max_y))
            for axis, maximum in (("x", max_x), ("y", max_y)):
                self._position_goals[axis] = max(0.0, min(self._position_goals[axis], maximum))

    def on_window_resized(self, boundary):
        """Fit the face inside half the window and recenter it after a resize."""
        width, height = (max(0.0, float(value)) for value in boundary)
        with self._pose_lock:
            self.boundary = [width, height]
            desired_factor = min(width * 0.5 / PHI, height * 0.5)
            # Window fitting takes precedence over the manual size controls so
            # the face remains half-window sized on both small and large displays.
            self.size_factor = max(1.0, desired_factor)
            self.size = [int(PHI * self.size_factor), int(self.size_factor)]
            self._layout_dirty = True
            center = (
                max(0.0, (width - self.size[0]) / 2),
                max(0.0, (height - self.size[1]) / 2),
            )
            self.set_position(center)
            for axis in ("x", "y"):
                self._position_goals[axis] = self._position_component(axis)
                self._position_speeds[axis] = None

    def get_position_bounds(self):
        with self._pose_lock:
            return {"x": {"min": 0.0, "max": max(0.0, self.boundary[0] - self.size[0] - self.boundary_margin)},
                    "y": {"min": 0.0, "max": max(0.0, self.boundary[1] - self.size[1] - self.boundary_margin)},
                    "window": {"width": self.boundary[0], "height": self.boundary[1]},
                    "face": {"width": self.size[0], "height": self.size[1]},
                    "margin": self.boundary_margin}

    @staticmethod
    def _add(a, b):
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    @staticmethod
    def _scale(vector, amount):
        return (vector[0] * amount, vector[1] * amount, vector[2] * amount)

    @staticmethod
    def _dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    @classmethod
    def _normalize(cls, vector):
        length = math.sqrt(cls._dot(vector, vector))
        return cls._scale(vector, 1.0 / length) if length else (0.0, 0.0, 0.0)

    @classmethod
    def _rotate_axis(cls, vector, axis, angle):
        axis = cls._normalize(axis)
        cosine, sine = math.cos(angle), math.sin(angle)
        return cls._add(
            cls._add(cls._scale(vector, cosine), cls._scale(cls._cross(axis, vector), sine)),
            cls._scale(axis, cls._dot(axis, vector) * (1.0 - cosine)),
        )

    def move_on_sphere(self, horizontal, vertical, dt_seconds):
        """Move the face's contact point over the sphere without adding roll."""
        speed = float(self.spherical.get("translation_speed", 1.15))
        with self._pose_lock:
            normal = self.sphere_normal
            if horizontal:
                normal = self._rotate_axis(normal, (0.0, 1.0, 0.0), -horizontal * speed * dt_seconds)
            if vertical:
                normal = self._rotate_axis(normal, (1.0, 0.0, 0.0), vertical * speed * dt_seconds)
            self.sphere_normal = self._normalize(normal)
            if horizontal or vertical:
                longitude, latitude = self._surface_angles()
                self._surface_goals.update(longitude=longitude, latitude=latitude)
                self._surface_speeds["longitude"] = None
                self._surface_speeds["latitude"] = None

    def rotate_on_sphere(self, amount, dt_seconds):
        speed = float(self.spherical.get("rotation_speed", 1.15))
        with self._pose_lock:
            self.sphere_roll += amount * speed * dt_seconds
            if amount:
                self._surface_goals["roll"] = self._wrap_angle(self.sphere_roll)
                self._surface_speeds["roll"] = None

    def move_camera_depth(self, amount, dt_seconds):
        speed = float(self.spherical.get("z_translation_speed", 220.0))
        with self._pose_lock:
            self.camera_distance += amount * speed * dt_seconds
            self.camera_distance = max(self.camera_distance, self._minimum_camera_distance())
            self._position_goals["z"] = self.camera_distance
            self._position_speeds["z"] = None

    def _minimum_camera_distance(self):
        margin = float(self.spherical.get("camera_margin", 35.0))
        return self.sphere_radius + math.hypot(self.size[0] / 2, self.size[1] / 2) + margin

    @staticmethod
    def _finite_number(value, name):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"'{name}' must be a finite number")
        return float(value)

    @classmethod
    def _validate_speed(cls, speed):
        speed = cls._finite_number(speed, "speed")
        if speed < 0:
            raise ValueError("'speed' must be zero (immediate) or positive")
        return speed

    def set_position_goal(self, x=None, y=None, z=None, speed=0.0):
        """Set an XYZ target; speed is in render units/second, zero is immediate."""
        speed = self._validate_speed(speed)
        values = {axis: value for axis, value in (("x", x), ("y", y), ("z", z))
                  if value is not None}
        if not values:
            raise ValueError("At least one of 'x', 'y', or 'z' is required")
        with self._pose_lock:
            for axis, value in values.items():
                value = self._finite_number(value, axis)
                if axis == "x":
                    value = max(0.0, min(value, self.boundary[0] - self.size[0] - self.boundary_margin))
                elif axis == "y":
                    value = max(0.0, min(value, self.boundary[1] - self.size[1] - self.boundary_margin))
                else:
                    value = max(value, self._minimum_camera_distance())
                self._position_goals[axis] = value
                self._position_speeds[axis] = speed or None
                if speed == 0:
                    self._set_position_component(axis, value)
        return self.get_pose()["position_goal"]

    def cancel_position_goal(self, axes=("x", "y", "z")):
        with self._pose_lock:
            for axis in axes:
                current = self._position_component(axis)
                self._position_goals[axis] = current
                self._position_speeds[axis] = None

    def _position_component(self, axis):
        return self.camera_distance if axis == "z" else float(self.position[0 if axis == "x" else 1])

    def _set_position_component(self, axis, value):
        if axis == "z":
            self.camera_distance = value
        elif axis == "x":
            self.position[0] = value
        else:
            self.position[1] = value

    @staticmethod
    def _wrap_angle(angle):
        return (angle + math.pi) % math.tau - math.pi

    def _surface_angles(self):
        normal = self._normalize(self.sphere_normal)
        latitude = math.asin(max(-1.0, min(1.0, normal[1])))
        longitude = math.atan2(normal[0], -normal[2])
        return longitude, latitude

    @staticmethod
    def _normal_from_angles(longitude, latitude):
        return (
            math.sin(longitude) * math.cos(latitude),
            math.sin(latitude),
            -math.cos(longitude) * math.cos(latitude),
        )

    def set_surface_goal(self, longitude=None, latitude=None, roll=None, speed=0.0):
        """Set spherical position and roll goals in radians; speed is radians/second."""
        speed = self._validate_speed(speed)
        values = {key: value for key, value in (
            ("longitude", longitude), ("latitude", latitude), ("roll", roll)
        ) if value is not None}
        if not values:
            raise ValueError("At least one surface parameter is required")
        with self._pose_lock:
            for axis, value in values.items():
                value = self._finite_number(value, axis)
                if axis == "latitude":
                    value = max(-math.pi / 2, min(value, math.pi / 2))
                else:
                    value = self._wrap_angle(value)
                self._surface_goals[axis] = value
                self._surface_speeds[axis] = speed or None
                if speed == 0:
                    if axis == "roll":
                        self.sphere_roll = value
                    else:
                        current = list(self._surface_angles())
                        current[0 if axis == "longitude" else 1] = value
                        self.sphere_normal = self._normal_from_angles(*current)
        return self.get_pose()["surface_goal"]

    @staticmethod
    def _approach(current, target, step, angular=False):
        difference = Face._wrap_angle(target - current) if angular else target - current
        if abs(difference) <= step:
            return target, True
        return current + math.copysign(step, difference), False

    def update_pose_goals(self, dt_ms):
        dt_seconds = max(0.0, min(float(dt_ms or 0) / 1000.0, 0.05))
        with self._pose_lock:
            for axis, speed in self._position_speeds.items():
                if speed is None:
                    continue
                current = self._position_component(axis)
                updated, reached = self._approach(
                    current, self._position_goals[axis], speed * dt_seconds
                )
                self._set_position_component(axis, updated)
                if reached:
                    self._position_speeds[axis] = None
            self.set_position(self.position)

            longitude, latitude = self._surface_angles()
            current_values = {"longitude": longitude, "latitude": latitude,
                              "roll": self.sphere_roll}
            updated_values = dict(current_values)
            for axis, speed in self._surface_speeds.items():
                if speed is None:
                    continue
                updated, reached = self._approach(
                    current_values[axis], self._surface_goals[axis], speed * dt_seconds,
                    angular=axis != "latitude",
                )
                updated_values[axis] = updated
                if reached:
                    self._surface_speeds[axis] = None
            self.sphere_normal = self._normal_from_angles(
                updated_values["longitude"], updated_values["latitude"]
            )
            self.sphere_roll = updated_values["roll"]

    def get_pose(self):
        with self._pose_lock:
            longitude, latitude = self._surface_angles()
            return {
                "position": {"x": self._position_component("x"),
                             "y": self._position_component("y"),
                             "z": self._position_component("z")},
                "position_goal": dict(self._position_goals),
                "surface": {"longitude": longitude, "latitude": latitude,
                            "roll": self._wrap_angle(self.sphere_roll)},
                "surface_goal": dict(self._surface_goals),
            }

    def _spherical_frame(self):
        normal = self.sphere_normal
        right = self._add(
            self.sphere_reference_right,
            self._scale(normal, -self._dot(self.sphere_reference_right, normal)),
        )
        if self._dot(right, right) < 1e-12:
            up = self._add(
                self.sphere_reference_up,
                self._scale(normal, -self._dot(self.sphere_reference_up, normal)),
            )
            right = self._cross(normal, self._normalize(up))
        right = self._normalize(right)
        up = self._normalize(self._cross(right, normal))
        return (
            self._rotate_axis(right, normal, self.sphere_roll),
            self._rotate_axis(up, normal, self.sphere_roll),
        )

    def _draw_spherical(self, surface):
        with self._pose_lock:
            self._draw_spherical_locked(surface)

    def _draw_spherical_locked(self, surface):
        width, height = self.size
        radius = self.sphere_radius
        margin = float(self.spherical.get("camera_margin", 35.0))
        minimum_distance = radius + math.hypot(width / 2, height / 2) + margin
        camera_distance = max(self.camera_distance, minimum_distance)
        anchor_x = self.position[0] + width / 2
        anchor_y = self.position[1] + height / 2
        contact = self._scale(self.sphere_normal, radius)
        right, up = self._spherical_frame()
        half_width, half_height = width / 2, height / 2
        corners_3d = [
            self._add(contact, self._add(self._scale(right, -half_width), self._scale(up, half_height))),
            self._add(contact, self._add(self._scale(right, half_width), self._scale(up, half_height))),
            self._add(contact, self._add(self._scale(right, half_width), self._scale(up, -half_height))),
            self._add(contact, self._add(self._scale(right, -half_width), self._scale(up, -half_height))),
        ]

        projected = []
        for point in corners_3d:
            depth = camera_distance + point[2]
            if depth <= 5.0:
                return
            projected.append((
                anchor_x + point[0] * self.focal_length / depth,
                anchor_y - point[1] * self.focal_length / depth,
            ))

        source = np.float32([
            [0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1],
        ])
        destination = np.float32(projected)
        homography = cv2.getPerspectiveTransform(source, destination)
        rgb = pygame.surfarray.array3d(self.face_surface).transpose(1, 0, 2)
        alpha = pygame.surfarray.array_alpha(self.face_surface).transpose(1, 0)
        image = np.dstack((rgb, alpha))
        surface_width, surface_height = surface.get_size()
        warped = cv2.warpPerspective(
            image,
            homography,
            (surface_width, surface_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            # Match the opaque face background in RGB so interpolation at the
            # transparent warp edge cannot create a dark fringe.
            borderValue=(*self.color[:3], 0),
        )
        projected_surface = pygame.image.frombuffer(
            warped.tobytes(), (surface_width, surface_height), "RGBA"
        )
        surface.blit(projected_surface, (0, 0))

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
        if self.spherical_enabled:
            self._draw_spherical(surface)
        else:
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
