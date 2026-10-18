import random

class EmotionMapper:
    def __init__(self, emotion_step=5):
        self.emotion_step = emotion_step
        self.initial_emotion = [
            0, 0, 0, 100, 0, 0, 0,
            0, 0, 0, 100, 0, 0, 0,
            0, 0, 100, 0, 0, 0, 0, 100, 0, 0
        ]
        self.emotion_goal = self.emotion_dict_from_values(self.initial_emotion)

    def emotion_dict_from_values(self, values):
        keys = [
            'letl_a', 'letl_b', 'letl_c', 'lps',
            'lebl_a', 'lebl_b', 'lebl_c',
            'retl_a', 'retl_b', 'retl_c', 'rps',
            'rebl_a', 'rebl_b', 'rebl_c',
            'tl_a', 'tl_b', 'tl_c', 'tl_d', 'tl_e',
            'bl_a', 'bl_b', 'bl_c', 'bl_d', 'bl_e'
        ]
        return dict(zip(keys, values))

    def get_emotion(self, hewo):
        letl, lps, lebl = hewo.left_eye.get_emotion()
        retl, rps, rebl = hewo.right_eye.get_emotion()
        tl, bl = hewo.mouth.get_emotion()
        return {
            'letl_a': letl[0], 'letl_b': letl[1], 'letl_c': letl[2],
            'lps': lps,
            'lebl_a': lebl[0], 'lebl_b': lebl[1], 'lebl_c': lebl[2],
            'retl_a': retl[0], 'retl_b': retl[1], 'retl_c': retl[2],
            'rps': rps,
            'rebl_a': rebl[0], 'rebl_b': rebl[1], 'rebl_c': rebl[2],
            'tl_a': tl[0], 'tl_b': tl[1], 'tl_c': tl[2], 'tl_d': tl[3], 'tl_e': tl[4],
            'bl_a': bl[0], 'bl_b': bl[1], 'bl_c': bl[2], 'bl_d': bl[3], 'bl_e': bl[4]
        }

    def set_emotion(self, hewo, emotion_dict):
        letl = [emotion_dict['letl_a'], emotion_dict['letl_b'], emotion_dict['letl_c']]
        lps = emotion_dict['lps']
        lebl = [emotion_dict['lebl_a'], emotion_dict['lebl_b'], emotion_dict['lebl_c']]
        retl = [emotion_dict['retl_a'], emotion_dict['retl_b'], emotion_dict['retl_c']]
        rps = emotion_dict['rps']
        rebl = [emotion_dict['rebl_a'], emotion_dict['rebl_b'], emotion_dict['rebl_c']]
        tl = [emotion_dict['tl_a'], emotion_dict['tl_b'], emotion_dict['tl_c'], emotion_dict['tl_d'], emotion_dict['tl_e']]
        bl = [emotion_dict['bl_a'], emotion_dict['bl_b'], emotion_dict['bl_c'], emotion_dict['bl_d'], emotion_dict['bl_e']]
        hewo.left_eye.set_emotion(letl, lps, lebl)
        hewo.right_eye.set_emotion(retl, rps, rebl)
        hewo.mouth.set_emotion(tl, bl)

    def transition(self, hewo):
        start = self.get_emotion(hewo)
        goal = self.emotion_goal
        diffs = []
        for key in start.keys():
            diff = goal[key] - start[key]
            if diff > 0:
                start[key] += min(diff, self.emotion_step)
            elif diff < 0:
                start[key] += max(diff, -self.emotion_step)
            diffs.append(goal[key] - start[key])
        return start, diffs

    def update_emotion(self, hewo):
        new_emotion, _ = self.transition(hewo)
        self.set_emotion(hewo, new_emotion)

    def set_random_emotion(self):
        random_emotion = [random.randint(0, 100) for _ in range(len(self.emotion_goal))]
        self.emotion_goal = self.emotion_dict_from_values(random_emotion)

    def reset_emotion(self):
        self.emotion_goal = self.emotion_dict_from_values(self.initial_emotion)
        return self.initial_emotion
