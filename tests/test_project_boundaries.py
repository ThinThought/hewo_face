import unittest
from unittest.mock import patch
import pygame

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

    def test_fullscreen_resize_notification_without_w_h_keeps_fullscreen_surface(self):
        class Screen:
            def get_size(self):
                return (1920, 1080)

        class Layout:
            boundary = None

            def set_boundary(self, boundary):
                self.boundary = boundary

            def handle_event(self, event):
                pass

        window = MainWindow.__new__(MainWindow)
        screen = Screen()
        layout = Layout()
        window.screen = screen
        window.settings = {"deploy": True}
        window.window_size = (1920, 1080)
        window.active_layout = "hewo"
        window.layout_dict = {"hewo": layout}
        resize_event = pygame.event.Event(pygame.WINDOWRESIZED, {"x": 1920, "y": 1080})
        with patch("pygame.event.get", return_value=[resize_event]), patch(
            "pygame.display.get_surface", return_value=screen
        ), patch("pygame.display.set_mode") as set_mode:
            window.handle_events()
        set_mode.assert_not_called()
        self.assertIs(window.screen, screen)
        self.assertEqual(layout.boundary, (1920, 1080))

    def test_only_changed_window_size_triggers_layout_resize_callback(self):
        class Screen:
            def __init__(self, size):
                self.size = size

            def get_size(self):
                return self.size

        class Layout:
            def __init__(self):
                self.resized = []

            def on_window_resized(self, size):
                self.resized.append(size)

            def set_boundary(self, size):
                pass

            def handle_event(self, event):
                pass

        window = MainWindow.__new__(MainWindow)
        layout = Layout()
        window.screen = Screen((800, 600))
        window.window_size = (800, 600)
        window.settings = {"deploy": False, "vsync": False}
        window.active_layout = "hewo"
        window.layout_dict = {"hewo": layout}
        resized_surface = Screen((1000, 700))
        event = pygame.event.Event(pygame.VIDEORESIZE, {"w": 1000, "h": 700})
        with patch("pygame.event.get", return_value=[event]), patch(
            "pygame.display.set_mode", return_value=resized_surface
        ):
            window.handle_events()
        self.assertEqual(layout.resized, [(1000, 700)])


if __name__ == "__main__":
    unittest.main()
