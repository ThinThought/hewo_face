import pygame
import copy
import numpy as np
from scipy.interpolate import make_interp_spline
from hewo.settings import create_logger


class EyeLash:
    def __init__(self, size, position, settings, object_name="EyeLash"):
        self.logger = create_logger(object_name)
        self.settings = copy.deepcopy(settings)

        self.set_size(size)
        self.set_position(position)
        self.emotion = self.settings["emotion"]
        self.color = self.settings["color"]

        x, y = self.position
        w, h = self.size
        self.polygon_points = [
            [0 + x, 0 + y],
            [0 + x, h + y],
            [w / 2 + x, h + y],
            [w + x, h + y],
            [w + x, 0 + y],
            [w / 2 + x, 0 + y],
        ]

        self.flip = self.settings["flip"]
        self.set_emotion(self.settings["emotion"])

        # ---------------------------------------------------------------------
        # Caché para evitar recalcular la spline cada frame
        # ---------------------------------------------------------------------
        self._cache_key = None          # (size, position, emotion tuple, flip)
        self._cached_polygon = None

    # -------------------------------------------------------------------------
    # Eventos / lógica
    # -------------------------------------------------------------------------
    def handle_event(self, event):
        pass

    def update(self):
        self.update_polygon_points()

    def update_polygon_points(self):
        x, y = self.position
        w, h = self.size
        self.polygon_points = [
            [0 + x, 0 + y],
            [0 + x, h + y],
            [w / 2 + x, h + y],
            [w + x, h + y],
            [w + x, 0 + y],
            [w / 2 + x, 0 + y],
        ]

        indices = [1, 2, 3] if not self.flip else [0, 5, 4]
        # Si flip está activo, invertimos la emoción (0 abierto, 100 cerrado)
        values = [100 - e if self.flip else e for e in self.emotion]

        for idx, val in zip(indices, values):
            self.polygon_points[idx][1] = self.position[1] + self.size[1] * (
                val / 100
            )

    # -------------------------------------------------------------------------
    # Dibujo con spline cacheada
    # -------------------------------------------------------------------------
    def create_polygon(self):
        # Generamos una clave única para la configuración actual
        key = (
            tuple(self.size),
            tuple(self.position),
            tuple(self.emotion),
            self.flip,
        )
        if key == self._cache_key and self._cached_polygon is not None:
            return self._cached_polygon

        points = self.polygon_points[1:4]
        if self.flip:
            points = [
                self.polygon_points[0],
                self.polygon_points[5],
                self.polygon_points[4],
            ]

        # Spline cuadrática
        x_points = np.array([p[0] for p in points])
        y_points = np.array([p[1] for p in points])
        spline = make_interp_spline(x_points, y_points, k=2)
        x_range = np.linspace(min(x_points), max(x_points), 500)
        interpolated_points = [(int(x), int(spline(x))) for x in x_range]

        polygon = [self.polygon_points[0]] + interpolated_points + self.polygon_points[4:]
        if self.flip:
            interpolated_points.reverse()
            polygon = self.polygon_points[1:4] + interpolated_points

        # Almacenamos en caché
        self._cache_key = key
        self._cached_polygon = polygon
        return polygon

    def draw(self, surface):
        polygon = self.create_polygon()
        pygame.draw.polygon(surface, self.color, polygon)

    # -------------------------------------------------------------------------
    # Setters geters
    # -------------------------------------------------------------------------
    def set_size(self, size):
        if size != getattr(self, "size", None):
            self.size = size
            self.max_emotion = self.size[1]
            self._cache_key = None  # invalida caché

    def set_position(self, position):
        if position != getattr(self, "position", None):
            self.position = position
            self._cache_key = None  # invalida caché

    def get_emotion(self):
        return self.emotion

    def set_emotion(self, emotion):
        changed = False
        for i, e in enumerate(emotion):
            clamped = max(0, min(e, 100))
            if clamped != self.emotion[i]:
                self.emotion[i] = clamped
                changed = True
        if changed:
            self._cache_key = None  # invalida caché


class Pupil:
    def __init__(self, size, position, settings, object_name="Pupil"):
        self.logger = create_logger(object_name)
        self.set_size(size)
        self.set_position(position)
        self.color = settings["color"]
        self.emotion = settings["emotion"][0]
        self.logger.info(f"position: {self.position}")
        self.logger.info(f"size: {self.size}")

    # -------------------------------------------------------------------------
    # Lógica
    # -------------------------------------------------------------------------
    def update(self):
        pass

    # -------------------------------------------------------------------------
    # Setters
    # -------------------------------------------------------------------------
    def set_size(self, size):
        self.size = size

    def set_position(self, position):
        self.position = position

    def handle_event(self, event):
        pass

    def set_emotion(self, emotion):
        self.emotion = max(0, min(emotion, 100))

    def get_emotion(self):
        return self.emotion

    # -------------------------------------------------------------------------
    # Dibujo
    # -------------------------------------------------------------------------
    def draw(self, surface):
        # Tamaño de la pupila en función de la emoción
        scale = self.emotion / 100  # 0..1
        ellipse_width = self.size[0] * scale
        ellipse_height = self.size[1] * scale

        # Coordenadas centradas
        ellipse_x = (self.size[0] - ellipse_width) / 2
        ellipse_y = (self.size[1] - ellipse_height) / 2

        pygame.draw.ellipse(
            surface, self.color, (ellipse_x, ellipse_y, ellipse_width, ellipse_height)
        )
