"""Canonical schema and transfer between emotion values and face components."""

import random
import math
from collections.abc import Mapping


EMOTION_KEYS = (
    "letl_a", "letl_b", "letl_c", "lps", "lebl_a", "lebl_b", "lebl_c",
    "retl_a", "retl_b", "retl_c", "rps", "rebl_a", "rebl_b", "rebl_c",
    "tl_a", "tl_b", "tl_c", "tl_d", "tl_e",
    "bl_a", "bl_b", "bl_c", "bl_d", "bl_e",
)

DEFAULT_EMOTION = dict(zip(EMOTION_KEYS, (
    0, 0, 0, 100, 0, 0, 0,
    0, 0, 0, 100, 0, 0, 0,
    0, 0, 100, 0, 0,
    0, 0, 100, 0, 0,
)))


class EmotionMapper:
    """Owns the validated emotion goal and maps it to/from face components.

    Partial goal updates are supported; omitted parameters retain their current
    goal. Returned mappings are copies so callers cannot mutate state by alias.
    """

    keys = EMOTION_KEYS

    def __init__(self, emotion_step=5):
        if emotion_step <= 0:
            raise ValueError("emotion_step must be positive")
        self.emotion_step = emotion_step
        self.initial_emotion = dict(DEFAULT_EMOTION)
        self._emotion_goal = dict(DEFAULT_EMOTION)

    @property
    def emotion_goal(self):
        return dict(self._emotion_goal)

    @emotion_goal.setter
    def emotion_goal(self, values):
        self.set_goal(values)

    @staticmethod
    def _normalize_value(key, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Emotion value for '{key}' must be numeric")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"Emotion value for '{key}' must be numeric")
        normalized = max(0, min(100, value))
        return int(normalized) if float(normalized).is_integer() else normalized

    def set_goal(self, values):
        if not isinstance(values, Mapping):
            raise ValueError("Emotion goal must be a mapping")
        unknown = set(values) - set(self.keys)
        if unknown:
            raise ValueError(f"Unknown emotion parameter(s): {', '.join(sorted(unknown))}")
        normalized = {key: self._normalize_value(key, value) for key, value in values.items()}
        self._emotion_goal.update(normalized)
        return self.emotion_goal

    def adjust_goal(self, key, delta):
        if key not in self._emotion_goal:
            raise ValueError(f"Unknown emotion parameter: {key}")
        return self.set_goal({key: self._emotion_goal[key] + delta})[key]

    def emotion_dict_from_values(self, values):
        if len(values) != len(self.keys):
            raise ValueError(f"Expected {len(self.keys)} emotion values, received {len(values)}")
        return {key: self._normalize_value(key, value) for key, value in zip(self.keys, values)}

    def get_emotion(self, hewo):
        letl, lps, lebl = hewo.left_eye.get_emotion()
        retl, rps, rebl = hewo.right_eye.get_emotion()
        tl, bl = hewo.mouth.get_emotion()
        values = (*letl, lps, *lebl, *retl, rps, *rebl, *tl, *bl)
        return dict(zip(self.keys, values))

    def set_emotion(self, hewo, emotion_dict):
        values = self.emotion_dict_from_values([emotion_dict[key] for key in self.keys])
        hewo.left_eye.set_emotion(
            [values[f"letl_{suffix}"] for suffix in "abc"], values["lps"],
            [values[f"lebl_{suffix}"] for suffix in "abc"],
        )
        hewo.right_eye.set_emotion(
            [values[f"retl_{suffix}"] for suffix in "abc"], values["rps"],
            [values[f"rebl_{suffix}"] for suffix in "abc"],
        )
        hewo.mouth.set_emotion(
            [values[f"tl_{suffix}"] for suffix in "abcde"],
            [values[f"bl_{suffix}"] for suffix in "abcde"],
        )

    def _transition_values(self, current):
        next_values = {
            key: current[key] + max(-self.emotion_step, min(self.emotion_step, self._emotion_goal[key] - current[key]))
            for key in self.keys
        }
        diffs = [self._emotion_goal[key] - next_values[key] for key in self.keys]
        return next_values, diffs

    def transition(self, hewo):
        return self._transition_values(self.get_emotion(hewo))

    def update_emotion(self, hewo):
        current = self.get_emotion(hewo)
        if all(current[key] == self._emotion_goal[key] for key in self.keys):
            return
        new_emotion, _ = self._transition_values(current)
        self.set_emotion(hewo, new_emotion)

    def set_random_emotion(self):
        self.set_goal({key: random.randint(0, 100) for key in self.keys})

    def reset_emotion(self):
        self._emotion_goal = dict(self.initial_emotion)
        return self.emotion_goal
