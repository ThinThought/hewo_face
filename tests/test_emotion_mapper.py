import unittest

from hewo.objects.hewo.logic.emotion_mapper import EMOTION_KEYS, EmotionMapper
from hewo.objects.hewo.curves import quadratic_basis, sample_quadratic
from hewo.objects.hewo.eye_components import EyeLash
from unittest.mock import patch


class Component:
    def __init__(self, emotion):
        self.emotion = emotion

    def get_emotion(self):
        return self.emotion


class Eye(Component):
    def set_emotion(self, top, pupil, bottom):
        self.emotion = (top, pupil, bottom)


class Mouth(Component):
    def set_emotion(self, top, bottom):
        self.emotion = (top, bottom)


class Face:
    def __init__(self):
        self.left_eye = Eye(([0, 0, 0], 100, [0, 0, 0]))
        self.right_eye = Eye(([0, 0, 0], 100, [0, 0, 0]))
        self.mouth = Mouth(([0, 0, 100, 0, 0], [0, 0, 100, 0, 0]))


class EmotionMapperTests(unittest.TestCase):
    def test_initial_and_reset_emotions_preserve_original_values(self):
        mapper = EmotionMapper()
        expected = mapper.emotion_dict_from_values([
            0, 0, 0, 100, 0, 0, 0,
            0, 0, 0, 100, 0, 0, 0,
            0, 0, 100, 0, 0,
            0, 0, 100, 0, 0,
        ])

        self.assertEqual(mapper.emotion_goal, expected)
        self.assertEqual(mapper.emotion_goal["bl_c"], 100)
        self.assertEqual(mapper.emotion_goal["bl_d"], 0)
        mapper.set_goal({"bl_d": 85})
        self.assertEqual(mapper.reset_emotion(), expected)

    def test_vectorized_quadratic_interpolates_the_three_controls(self):
        xs, weights = quadratic_basis((0, 5, 10), 3)
        points = sample_quadratic(xs, weights, (1, 4, 9))
        self.assertEqual(points, [(0, 1), (5, 4), (10, 9)])

    def test_static_eyelash_geometry_is_not_rebuilt_each_update(self):
        lash = EyeLash((100, 50), (0, 0), {
            "emotion": [0, 0, 0], "color": (0, 0, 0), "flip": False,
        })
        lash.update()
        with patch.object(lash, "update_polygon_points", wraps=lash.update_polygon_points) as rebuild:
            for _ in range(20):
                lash.update()
            rebuild.assert_not_called()
            lash.set_emotion([10, 0, 0])
            lash.update()
            rebuild.assert_called_once()

    def test_goal_updates_are_partial_clamped_and_defensive(self):
        mapper = EmotionMapper()
        mapper.set_goal({"lps": 140, "tl_a": -10})
        self.assertEqual(mapper.emotion_goal["lps"], 100)
        self.assertEqual(mapper.emotion_goal["tl_a"], 0)
        self.assertEqual(mapper.emotion_goal["rps"], 100)
        exposed = mapper.emotion_goal
        exposed["lps"] = 12
        self.assertEqual(mapper.emotion_goal["lps"], 100)

    def test_rejects_unknown_missing_shape_and_non_finite_values(self):
        mapper = EmotionMapper()
        with self.assertRaises(ValueError):
            mapper.set_goal({"not_a_parameter": 5})
        with self.assertRaises(ValueError):
            mapper.set_goal({"lps": float("nan")})
        with self.assertRaises(ValueError):
            mapper.emotion_dict_from_values([0])

    def test_key_order_round_trips_all_component_values(self):
        mapper = EmotionMapper()
        face = Face()
        values = {key: i for i, key in enumerate(EMOTION_KEYS)}
        mapper.set_emotion(face, values)
        self.assertEqual(mapper.get_emotion(face), values)

    def test_transition_moves_each_value_by_at_most_step(self):
        mapper = EmotionMapper(emotion_step=5)
        face = Face()
        mapper.set_goal({"lps": 0, "tl_a": 100})
        next_values, remaining = mapper.transition(face)
        self.assertEqual(next_values["lps"], 95)
        self.assertEqual(next_values["tl_a"], 5)
        self.assertEqual(remaining[EMOTION_KEYS.index("lps")], -95)
        self.assertEqual(remaining[EMOTION_KEYS.index("tl_a")], 95)

    def test_fractional_internal_values_support_talking_animation(self):
        mapper = EmotionMapper(emotion_step=5)
        face = Face()
        mapper.set_goal({"tl_c": 83.5})
        mapper.update_emotion(face)
        self.assertEqual(mapper.get_emotion(face)["tl_c"], 95)
        for _ in range(3):
            mapper.update_emotion(face)
        self.assertEqual(mapper.get_emotion(face)["tl_c"], 83.5)

    def test_api_returns_client_error_for_unknown_emotion_key(self):
        from hewo.main.endpoint import ServerEndPoint

        class Layout:
            def adjust_emotion(self, key, value):
                EmotionMapper().set_goal({key: value})

        class Window:
            active_layout = "face"
            layout_dict = {"face": Layout()}

            def get_active_layout(self):
                return self.layout_dict.get(self.active_layout)

            def set_active_layout(self, key):
                self.active_layout = key

        response = ServerEndPoint(Window()).app.test_client().post(
            "/hewo/adjust_emotion/unknown", json={"value": 10}
        )
        self.assertEqual(response.status_code, 400)

    def test_api_handles_stale_active_layout(self):
        from hewo.main.endpoint import ServerEndPoint

        class Window:
            active_layout = "removed"
            layout_dict = {}

            def get_active_layout(self):
                return self.layout_dict.get(self.active_layout)

        response = ServerEndPoint(Window()).app.test_client().post("/hewo/toggle_talk")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
