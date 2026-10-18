import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame

from hewo.objects.multimedia.multimedia import Multimedia


class VideoFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((2, 2))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_video_frame_is_scaled_before_surface_conversion(self):
        media = Multimedia.__new__(Multimedia)
        media.target_size = (2, 1)
        media.rect = pygame.Rect(5, 7, 0, 0)
        # OpenCV BGR pixels; expected display color is RGB (30, 20, 10).
        frame = np.full((4, 4, 3), (10, 20, 30), dtype=np.uint8)

        media._frame_to_surface(frame)

        self.assertEqual(media.surface.get_size(), (2, 1))
        self.assertEqual(media.surface.get_at((0, 0))[:3], (30, 20, 10))
        self.assertEqual(media.rect.topleft, (5, 7))

    def test_opencv_is_not_imported_until_a_video_frame_is_processed(self):
        self.assertNotIn("cv2", sys.modules)


if __name__ == "__main__":
    unittest.main()
