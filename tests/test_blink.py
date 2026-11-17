import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from hewo.objects.hewo.hewo import HeWo
from hewo.settings import SettingsLoader


class BlinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def make(self):
        return HeWo(settings=SettingsLoader().load_settings("hewo.settings.hewo"))

    def test_hewo_never_blinks_on_its_own(self):
        hewo = self.make()
        for _ in range(1500):
            hewo._core_update()
            self.assertFalse(hewo.left_eye.blinking or hewo.right_eye.blinking)

    def test_manual_blink_still_works(self):
        hewo = self.make()
        hewo.trigger_blink()
        self.assertTrue(hewo.left_eye.blinking and hewo.right_eye.blinking)

    def test_blink_closes_then_reopens_gradually_to_the_previous_shape(self):
        hewo = self.make()
        goal = {"letl_a": 0, "letl_b": 50, "letl_c": 100, "lebl_a": 30, "lebl_b": 60, "lebl_c": 30}
        hewo.set_emotion_goal(goal, immediate=True)
        hewo.update(16)
        before = hewo.left_eye.get_emotion()
        before = (list(before[0]), before[1], list(before[2]))
        hewo.trigger_blink()
        frames_closed = 0
        for _ in range(25):  # 23 closing + 2 opening frames
            hewo.update(16)
            if hewo.left_eye.get_emotion()[0] == [100, 100, 100]:
                frames_closed += 1
        self.assertGreater(frames_closed, 0)
        # The eye ends closed and then reopens gradually (5 units per frame)
        # towards the emotion goal, as the original animation did.
        reopening = []
        for _ in range(25):
            hewo.update(16)
            reopening.append(hewo.left_eye.get_emotion()[0][0])
        self.assertTrue(any(0 < value < 100 for value in reopening))
        after = hewo.left_eye.get_emotion()
        self.assertEqual((after[0], after[2]), (before[0], before[2]))


if __name__ == "__main__":
    unittest.main()
