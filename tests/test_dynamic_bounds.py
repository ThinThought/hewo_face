import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from hewo.main.endpoint import ServerEndPoint
from hewo.objects.hewo import HeWo
from hewo.settings import SettingsLoader


class DynamicBoundsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        settings = SettingsLoader().load_settings("hewo.settings.hewo")
        self.hewo = HeWo(settings)

    def test_resize_clamps_current_position_and_pending_xy_goal(self):
        self.hewo.boundary_margin = 12
        self.hewo.set_position_goal(x=900, y=600, speed=20)
        self.hewo.set_boundary((500, 350))
        limits = self.hewo.get_position_bounds()

        self.assertEqual(limits["x"]["max"], 500 - self.hewo.size[0] - 12)
        self.assertEqual(limits["y"]["max"], 350 - self.hewo.size[1] - 12)
        pose = self.hewo.get_pose()
        self.assertLessEqual(pose["position"]["x"], limits["x"]["max"])
        self.assertLessEqual(pose["position"]["y"], limits["y"]["max"])
        self.assertLessEqual(pose["position_goal"]["x"], limits["x"]["max"])
        self.assertLessEqual(pose["position_goal"]["y"], limits["y"]["max"])

    def test_window_resize_centers_face_scales_to_half_and_cancels_old_xy_goal(self):
        self.hewo.set_position_goal(x=850, y=550, speed=20)
        self.hewo.on_window_resized((800, 600))

        pose = self.hewo.get_pose()
        self.assertAlmostEqual(pose["position"]["x"], (800 - self.hewo.size[0]) / 2)
        self.assertAlmostEqual(pose["position"]["y"], (600 - self.hewo.size[1]) / 2)
        self.assertLessEqual(self.hewo.size[0], 800 * 0.5)
        self.assertLessEqual(self.hewo.size[1], 600 * 0.5)
        self.assertEqual(pose["position_goal"]["x"], pose["position"]["x"])
        self.assertEqual(pose["position_goal"]["y"], pose["position"]["y"])

    def test_bounds_api_exposes_live_limits(self):
        window = type("Window", (), {"get_active_layout": lambda _self: self.hewo})()
        response = ServerEndPoint(window).app.test_client().get("/hewo/get_position_bounds")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["bounds"], self.hewo.get_position_bounds())


if __name__ == "__main__":
    unittest.main()
