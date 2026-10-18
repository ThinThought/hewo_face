import unittest
from unittest.mock import patch

from hewo.main.window import MainWindow
from hewo.settings import SettingsLoader


class ProjectBoundaryTests(unittest.TestCase):
    def test_settings_loader_does_not_leak_values_between_packages(self):
        loader = SettingsLoader()
        window_settings = loader.load_settings("hewo.settings.window")
        face_settings = loader.load_settings("hewo.settings.hewo")
        self.assertIn("window_title", window_settings)
        self.assertIn("face", face_settings)
        self.assertNotIn("window_title", face_settings)

    def test_window_update_propagates_layout_errors_without_retrying(self):
        class BrokenLayout:
            calls = 0

            def update(self, dt_ms):
                self.calls += 1
                raise TypeError("failure inside update")

        window = MainWindow.__new__(MainWindow)
        layout = BrokenLayout()
        window.active_layout = "active"
        window.layout_dict = {"active": layout}
        with self.assertRaisesRegex(TypeError, "failure inside update"):
            window.update(16)
        self.assertEqual(layout.calls, 1)

    def test_shutdown_delegates_cleanup_to_layouts(self):
        class Layout:
            closed = False

            def close(self):
                self.closed = True

        window = MainWindow.__new__(MainWindow)
        layout = Layout()
        window.layout_dict = {"resource_owner": layout}
        window._shutdown_media()
        self.assertTrue(layout.closed)

    def test_window_skips_background_fill_for_layout_that_clears_surface(self):
        class Screen:
            fills = 0

            def fill(self, color):
                self.fills += 1

        class Layout:
            clears_surface = True

            def draw(self, screen):
                pass

        window = MainWindow.__new__(MainWindow)
        window.screen = Screen()
        window.background_color = (0, 0, 0)
        window.active_layout = "media"
        window.layout_dict = {"media": Layout()}
        with patch("pygame.display.flip"):
            window.draw()
        self.assertEqual(window.screen.fills, 0)


if __name__ == "__main__":
    unittest.main()
