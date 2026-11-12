import copy
import math
import time
import pygame
from hewo.settings import create_logger
from hewo.objects.hewo.curves import through_point_bezier


class Lip:
    """Un labio (superior o inferior) con curva cacheada.

    Los puntos de emoción (0‒100) quedan confinados al contenedor de la boca,
    pero el trazo se dibuja con un margen (``offset``) para que la curva y su
    grosor puedan salir del contenedor sin recortarse.
    """

    def __init__(self, size, position, settings, object_name="Lip"):
        self.logger = create_logger(object_name)

        self.size = size
        self.position = position
        self.color = tuple(settings["color"])
        self.lip_width = settings["lip_width"]
        self.emotion = settings[
            "emotion"
        ]  # [x1, y1, center_y, x2, y2] porcentajes 0‒100

        # caché de la curva
        self._cache_key = None
        self._cached_points = None

    # --------------------------------------------------------------------- utils
    @staticmethod
    def clamp(value, min_value, max_value):
        return max(min_value, min(value, max_value))

    # --------------------------------------------------------------------- curva
    def control_points(self):
        """Comisura izquierda, centro y comisura derecha en píxeles del contenedor.

        En Y, 0..100 recorre el contenedor dejando medio grosor de labio en
        cada borde, de modo que un punto en el extremo se ve entero (la boca
        está pegada al borde inferior de la cara). La curva sí puede salir.
        """
        width, height = self.size
        half = width / 2
        inset = min(self.lip_width / 2, height / 2)
        span = height - 2 * inset
        e = [self.clamp(value, 0, 100) / 100 for value in self.emotion]
        left = (e[0] * half, inset + e[1] * span)
        center = (half, inset + e[2] * span)
        right = (width - e[3] * half, inset + e[4] * span)
        return left, center, right

    def lip_shape(self, offset=(0, 0)):
        """Puntos (int, int) del labio, desplazados por ``offset``.

        Es una Bézier cuadrática que pasa por la altura del centro: acotada
        aunque las comisuras se junten en el centro. Si tamaño + emoción no
        cambian, reutiliza la forma cacheada.
        """
        key = (tuple(self.size), tuple(self.emotion), tuple(offset))
        if key == self._cache_key and self._cached_points is not None:
            return self._cached_points

        ox, oy = offset
        left, center, right = (
            (x + ox, y + oy) for x, y in self.control_points()
        )
        points = through_point_bezier(left, center, right, 50)

        self._cache_key = key
        self._cached_points = points
        return points

    # --------------------------------------------------------------------- API
    def set_emotion(self, emotion_vector):
        if emotion_vector != self.emotion:
            self.emotion = emotion_vector
            self._cache_key = None  # invalida caché

    def get_emotion(self):
        return self.emotion

    def set_size(self, size):
        if size != self.size:
            self.size = size
            self._cache_key = None

    def update(self):
        pass

    def draw(self, surface, offset=(0, 0)):
        points = self.lip_shape(offset)
        pygame.draw.lines(surface, self.color, False, points, self.lip_width)

    def handle_event(self, event):
        pass


class Mouth:
    """Contenedor de los dos labios con superficie reutilizable."""

    def __init__(self, size, position, settings, object_name="Mouth"):
        self.logger = create_logger(object_name)
        self.settings = copy.deepcopy(settings)

        self.size = size
        self.position = position
        self.color = self.settings["bg_color"]
        # Margen transparente alrededor del contenedor (fracción de su tamaño)
        # donde los labios pueden dibujarse fuera de él sin recortarse.
        self.render_overflow = float(self.settings.get("render_overflow", 0.5))
        if self.render_overflow < 0:
            raise ValueError("render_overflow cannot be negative")

        # Labios
        self.top_lip = Lip(
            self.size,
            self.position,
            self.settings["upper_lip"],
            object_name=f"{object_name} - Top Lip",
        )
        self.bot_lip = Lip(
            self.size,
            self.position,
            self.settings["lower_lip"],
            object_name=f"{object_name} - Bot Lip",
        )

        # superficie persistente con margen, SRCALPHA para fondo transparente
        self.surface = pygame.Surface(self._surface_size(), pygame.SRCALPHA)
        self._layout_dirty = False  # marca recreación de superficie

        # Parámetros de habla
        self.talking_amplitude = self.settings["talking_amplitude"]
        self.talking_speed = self.settings["talking_speed"]
        self._talking_reference = {"top": self.top_lip.get_emotion(), "bot": self.bot_lip.get_emotion()}
        self.is_talking = False

    # --------------------------------------------------------------------- tamaño / posición
    def padding(self):
        """Margen (x, y) en píxeles entre la superficie y el contenedor."""
        lip_width = max(self.top_lip.lip_width, self.bot_lip.lip_width)
        return tuple(
            int(math.ceil(self.render_overflow * length + lip_width)) for length in self.size
        )

    def _surface_size(self):
        pad_x, pad_y = self.padding()
        return self.size[0] + 2 * pad_x, self.size[1] + 2 * pad_y

    def set_size(self, size):
        if size != self.size:
            self.size = size
            self.top_lip.set_size(size)
            self.bot_lip.set_size(size)
            self._layout_dirty = True

    def set_position(self, position):
        self.position = position  # se usa sólo en blit

    # --------------------------------------------------------------------- draw / update
    def draw(self, surface):
        if self._layout_dirty:
            self.surface = pygame.Surface(self._surface_size(), pygame.SRCALPHA)
            self._layout_dirty = False

        pad_x, pad_y = self.padding()
        # Solo el contenedor lleva fondo; el margen es transparente para no
        # tapar ojos ni cara cuando los labios salen del contenedor.
        self.surface.fill((0, 0, 0, 0))
        self.surface.fill(self.color, pygame.Rect(pad_x, pad_y, *self.size))
        self.top_lip.draw(self.surface, (pad_x, pad_y))
        self.bot_lip.draw(self.surface, (pad_x, pad_y))
        surface.blit(self.surface, (self.position[0] - pad_x, self.position[1] - pad_y))

    def update(self):
        self.top_lip.update()
        self.bot_lip.update()
        if self.is_talking:
            self.animate_talk()

    # --------------------------------------------------------------------- talk animation
    def set_talking_reference(self):
        self._talking_reference = {
            "top": self.top_lip.get_emotion(),
            "bot": self.bot_lip.get_emotion(),
        }

    def toggle_talk(self):
        if not self.is_talking:
            self.set_talking_reference()
            self.talking_start_time = time.time()
            self.is_talking = True
        else:
            self.is_talking = False
            self.top_lip.set_emotion(self._talking_reference["top"])
            self.bot_lip.set_emotion(self._talking_reference["bot"])

    def animate_talk(self):
        if not self.is_talking:
            return

        tick = (time.time() - self.talking_start_time) * self.talking_speed
        osc = abs(math.sin(tick)) * self.talking_amplitude

        base_top = self._talking_reference["top"]
        base_bot = self._talking_reference["bot"]
        center_y = (base_top[2] + base_bot[2]) / 2

        new_top = base_top[:]
        new_bot = base_bot[:]
        new_top[2] = center_y - osc
        new_bot[2] = center_y + osc

        self.top_lip.set_emotion(new_top)
        self.bot_lip.set_emotion(new_bot)

    # --------------------------------------------------------------------- emotion helpers
    def set_emotion(self, top_lip_percentages, bot_lip_percentages):
        self.top_lip.set_emotion(top_lip_percentages)
        self.bot_lip.set_emotion(bot_lip_percentages)
        self.set_talking_reference()

    def get_emotion(self):
        return self.top_lip.get_emotion(), self.bot_lip.get_emotion()

    # --------------------------------------------------------------------- eventos
    def handle_event(self, event):
        pass
