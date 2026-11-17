import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from hewo.objects.hewo.curves import quadratic_basis, sample_quadratic, through_point_bezier
from hewo.objects.hewo.mouth import Lip, Mouth


LIP = {"color": (255, 255, 255), "lip_width": 5, "emotion": [0, 0, 100, 0, 0]}


def mouth_settings(**overrides):
    settings = {
        "talking_amplitude": 50, "talking_speed": 10, "bg_color": (10, 20, 30),
        "upper_lip": dict(LIP, emotion=[0, 0, 100, 0, 0]),
        "lower_lip": dict(LIP, emotion=[0, 0, 100, 0, 0]),
    }
    settings.update(overrides)
    return settings


class CurveTests(unittest.TestCase):
    def test_matches_the_old_parabola_for_symmetric_lips(self):
        xs, weights = quadratic_basis((0, 50, 100), 11)
        old = sample_quadratic(xs, weights, (0, 40, 0))
        new = through_point_bezier((0, 0), (50, 40), (100, 0), 11)
        for (ox, oy), (nx, ny) in zip(old, new):
            self.assertLessEqual(abs(ox - nx), 1)
            self.assertLessEqual(abs(oy - ny), 1)

    def test_stays_bounded_when_corners_meet_the_center(self):
        for gap in (0.0, 0.01, 0.5, 2.0):
            points = through_point_bezier((50 - gap, 0), (50, 40), (50 + gap, 30), 50)
            ys = [y for _, y in points]
            self.assertLessEqual(max(ys), 80)  # control point height: 2*40 - 15 = 65
            self.assertGreaterEqual(min(ys), 0)
            xs = [x for x, _ in points]
            self.assertTrue(50 - gap - 1 <= min(xs) and max(xs) <= 50 + gap + 1)


class LipTests(unittest.TestCase):
    def test_corners_at_the_center_do_not_explode(self):
        lip = Lip([300, 60], [0, 0], dict(LIP, emotion=[100, 0, 100, 99, 10]))
        ys = [y for _, y in lip.lip_shape()]
        self.assertTrue(all(-60 <= y <= 120 for y in ys))

    def test_emotion_points_stay_confined_and_offset_moves_the_curve(self):
        lip = Lip([300, 60], [0, 0], dict(LIP, emotion=[-50, 150, 100, 0, 0]))
        left, center, right = lip.control_points()
        self.assertEqual(left, (0.0, 57.5))  # clamped to 100, half lip width inside
        self.assertEqual(right[1], 2.5)
        points = lip.lip_shape((10, 20))
        self.assertEqual(points[0], (10, 78))
        self.assertEqual(points[-1], (310, 22))


class MouthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_lips_can_render_outside_the_container(self):
        mouth = Mouth([200, 40], [100, 100], mouth_settings(render_overflow=0.5))
        pad_x, pad_y = mouth.padding()
        self.assertEqual((pad_x, pad_y), (105, 25))
        self.assertEqual(mouth.surface.get_size(), (410, 90))
        # An asymmetric lip bulges above the container (top at y=100): it is
        # drawn in the margin instead of being clipped.
        mouth.set_emotion([0, 0, 0, 0, 100], [0, 0, 0, 0, 100])
        target = pygame.Surface((400, 300), pygame.SRCALPHA)
        mouth.draw(target)
        lip_pixels = [
            y for x in range(100, 300) for y in range(60, 100)
            if target.get_at((x, y))[:3] == (255, 255, 255)
        ]
        self.assertTrue(lip_pixels)
        self.assertLess(min(lip_pixels), 97)
        # The overflow margin is transparent; only the container gets the background.
        self.assertEqual(target.get_at((200, 80)).a, 0)
        self.assertEqual(target.get_at((200, 120))[:3], (10, 20, 30))

    def test_negative_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            Mouth([200, 40], [0, 0], mouth_settings(render_overflow=-1))


if __name__ == "__main__":
    unittest.main()
