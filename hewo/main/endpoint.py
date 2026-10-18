import threading
import subprocess
from flask import Flask, request, jsonify

SERVER_IP = '0.0.0.0'
SERVER_PORT = 8000


class ServerEndPoint:
    def __init__(self, main_window):
        self.app = Flask(__name__)
        self.main_window = main_window
        self._speech_lock = threading.Lock()
        self._speech_signature = None
        self.setup_routes()

    def _speech_controller(self, config):
        """Configure and reuse a speech controller for the active HeWo layout."""
        layout = self.get_layout()
        if layout is None or not callable(getattr(layout, "say", None)):
            raise RuntimeError("The active layout does not support speech")

        backend = config.get("backend", "pocket_tts")
        if backend not in ("pocket_tts", "espeak_ng"):
            raise ValueError("backend must be 'pocket_tts' or 'espeak_ng'")
        language = config.get("language", "spanish")
        voice = config.get("voice")
        quantize = config.get("quantize", False)
        sampler_decode_steps = config.get("sampler_decode_steps", 1)
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty string")
        if voice is not None and (not isinstance(voice, str) or not voice.strip()):
            raise ValueError("voice must be a non-empty string or null")
        if not isinstance(quantize, bool):
            raise ValueError("quantize must be a boolean")
        if isinstance(sampler_decode_steps, bool) or not isinstance(sampler_decode_steps, int) or sampler_decode_steps < 1:
            raise ValueError("sampler_decode_steps must be a positive integer")
        signature = (backend, language.strip(), voice.strip() if voice else None,
                     quantize, sampler_decode_steps)

        with self._speech_lock:
            if getattr(layout, "speech_controller", None) is None or self._speech_signature != signature:
                old_controller = getattr(layout, "speech_controller", None)
                if old_controller is not None:
                    old_controller.close()
                if backend == "pocket_tts":
                    from hewo.objects.speech.backends.pocket_tts import PocketTTSEngine
                    engine = PocketTTSEngine(
                        language=signature[1], voice=signature[2], quantize=quantize,
                        sampler_decode_steps=sampler_decode_steps,
                    )
                else:
                    from hewo.objects.speech.backends.espeak_ng import EspeakNgEngine
                    engine = EspeakNgEngine(voice=signature[2] or signature[1])
                from hewo.objects.speech.controller import SpeechController
                from hewo.objects.speech.output import PygameAudioOutput
                layout.speech_controller = SpeechController(engine, PygameAudioOutput())
                self._speech_signature = signature
        return layout

    def get_layout(self):
        return self.main_window.get_active_layout()

    def require_layout_method(self, method):
        layout = self.get_layout()
        if layout is None or not callable(getattr(layout, method, None)):
            return None, (jsonify({"status": "error", "message": f"No active layout supports '{method}'"}), 400)
        return layout, None

    @staticmethod
    def _speech_options(backend):
        pocket_voices = {
            "english": ["cosette", "marius", "javert", "alba", "jean", "anna", "vera", "fantine", "charles", "paul", "eponine", "azelma", "george", "mary", "jane", "michael", "eve", "bill_boerst", "peter_yearsley", "stuart_bell", "caro_davy"],
            "spanish": ["lola"], "french": ["estelle"], "german": ["juergen"],
            "italian": ["giovanni"], "portuguese": ["rafael"], "dutch": ["daan"],
        }
        if backend == "pocket_tts":
            all_voices = [
                "cosette", "marius", "javert", "alba", "jean", "anna", "vera",
                "fantine", "charles", "paul", "eponine", "azelma", "george", "mary",
                "jane", "michael", "eve", "bill_boerst", "peter_yearsley", "stuart_bell",
                "caro_davy", "giovanni", "lola", "juergen", "rafael", "daan", "estelle",
            ]
            return {"languages": list(pocket_voices), "voices": all_voices, "voices_by_language": pocket_voices}
        if backend == "espeak_ng":
            try:
                output = subprocess.run(
                    ["espeak-ng", "--voices"], check=True, capture_output=True,
                    text=True, timeout=5,
                ).stdout
            except (OSError, subprocess.SubprocessError) as error:
                raise RuntimeError(f"Could not list eSpeak NG voices: {error}") from error
            voices = []
            for line in output.splitlines():
                columns = line.split()
                if len(columns) >= 5 and columns[0].isdigit():
                    voice = columns[4]
                    if voice not in voices:
                        voices.append(voice)
            if not voices:
                raise RuntimeError("eSpeak NG returned no installed voices")
            return {"languages": [], "voices": {"": voices}}
        raise ValueError("backend must be 'pocket_tts' or 'espeak_ng'")



    def setup_routes(self):
        @self.app.route('/hewo/speech_options', methods=['GET'])
        def speech_options():
            backend = request.args.get("backend", "pocket_tts")
            try:
                options = self._speech_options(backend)
                return jsonify({"status": "success", **options}), 200
            except ValueError as error:
                return jsonify({"status": "error", "message": str(error)}), 400
            except RuntimeError as error:
                return jsonify({"status": "error", "message": str(error)}), 503

        @self.app.route('/hewo/say', methods=['POST'])
        def say_text():
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"status": "error", "message": "Request body must be a JSON object"}), 400
            text = data.get("text")
            if not isinstance(text, str) or not text.strip():
                return jsonify({"status": "error", "message": "text must be a non-empty string"}), 400
            try:
                layout = self._speech_controller(data)
                layout.say(text)
                return jsonify({"status": "success", "message": "Speech queued"}), 202
            except (TypeError, ValueError, RuntimeError) as error:
                return jsonify({"status": "error", "message": str(error)}), 400
            except Exception as error:
                return jsonify({"status": "error", "message": str(error)}), 500

        @self.app.route('/set_layout', methods=['POST'])
        def set_layout():
            data = request.get_json()
            name = data.get("name")
            if name not in self.main_window.layout_dict:
                return jsonify({"status": "error", "message": f"Layout '{name}' not found"}), 404

            self.main_window.set_active_layout(name)
            return jsonify({"status": "success", "active_layout": name}), 200

        @self.app.route('/hewo/set_emotion_goal', methods=['POST'])
        def set_emotion():
            layout = self.get_layout()
            if not layout or not hasattr(layout, 'set_emotion_goal'):
                return jsonify({"status": "error", "message": "No valid layout for setting emotion"}), 400
            try:
                data = request.get_json()
                layout.set_emotion_goal(data)
                return jsonify({"status": "success"}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/hewo/get_emotion', methods=['GET'])
        def get_emotion():
            layout = self.get_layout()
            if not layout or not hasattr(layout, 'get_emotion'):
                return jsonify({"status": "error", "message": "No valid layout for getting emotion"}), 400
            try:
                emotion = layout.get_emotion()
                return jsonify({"status": "success", "emotion": emotion}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/hewo/toggle_talk', methods=['POST'])
        def toggle_talk():
            layout, error = self.require_layout_method('toggle_talk')
            if error:
                return error
            layout.toggle_talk()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/trigger_blink', methods=['POST'])
        def trigger_blink():
            layout, error = self.require_layout_method('trigger_blink')
            if error:
                return error
            layout.trigger_blink()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/adjust_position', methods=['POST'])
        def adjust_position():
            layout, error = self.require_layout_method('adjust_position')
            if error:
                return error
            data = request.get_json()
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            layout.adjust_position(dx, dy)
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/set_size', methods=['POST'])
        def adjust_size():
            layout, error = self.require_layout_method('set_face_size')
            if error:
                return error
            data = request.get_json()
            size = int(data.get("value", 0))
            layout.set_face_size(size)
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/set_random_emotion', methods=['POST'])
        def set_random_emotion():
            layout, error = self.require_layout_method('set_random_emotion')
            if error:
                return error
            layout.set_random_emotion()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/reset_emotion', methods=['POST'])
        def reset_emotion():
            layout, error = self.require_layout_method('reset_emotion')
            if error:
                return error
            layout.reset_emotion()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/adjust_emotion/<param>', methods=['POST'])
        def adjust_emotion(param):
            layout = self.get_layout()
            if not layout or not hasattr(layout, 'adjust_emotion'):
                return jsonify({"status": "error", "message": "No valid layout for adjusting emotion"}), 400
            data = request.get_json()
            try:
                if not isinstance(data, dict):
                    raise ValueError
                value = int(data.get("value"))
            except (TypeError, ValueError):
                return jsonify({"status": "error", "message": "Missing or invalid 'value' (must be int)"}), 400

            try:
                layout.adjust_emotion(param, value)
                return jsonify({"status": "success"}), 200
            except (TypeError, ValueError, KeyError) as e:
                return jsonify({"status": "error", "message": str(e)}), 400

        @self.app.route('/media/move', methods=['POST'])
        def move_media():
            layout, error = self.require_layout_method('move_object')
            if error:
                return error
            data = request.get_json()
            name = data.get("name")
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            layout.move_object(name, dx, dy)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/set_position', methods=['POST'])
        def set_position():
            layout, error = self.require_layout_method('set_position')
            if error:
                return error
            data = request.get_json()
            name = data.get("name")
            x = int(data.get("x", 0))
            y = int(data.get("y", 0))
            layout.set_position(name, x, y)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/pause', methods=['POST'])
        def pause_media():
            layout, error = self.require_layout_method('pause_object')
            if error:
                return error
            data = request.get_json()
            name = data.get("name")
            layout.pause_object(name)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/play', methods=['POST'])
        def play_media():
            layout, error = self.require_layout_method('play_object')
            if error:
                return error
            data = request.get_json()
            name = data.get("name")
            layout.play_object(name)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/remove', methods=['POST'])
        def remove_media():
            layout, error = self.require_layout_method('remove_by_name')
            if error:
                return error
            data = request.get_json()
            name = data.get("name")
            layout.remove_by_name(name)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/add', methods=['POST'])
        def add_media_object():
            layout = self.get_layout()
            if not layout or not hasattr(layout, 'add_object'):
                return jsonify({"status": "error", "message": "Not a valid multimedia layout"}), 400

            data = request.get_json()
            try:
                filepath = data["filepath"]
                position = tuple(data.get("position", [0, 0]))
                velocity = tuple(data.get("velocity", [0, 0]))
                size = tuple(data.get("size")) if "size" in data else None
                loop = data.get("loop", True)
                audio = data.get("audio", False)
                name = data.get("name", "NewMediaObj")

                from hewo.objects.multimedia import MultimediaGameObj
                obj = MultimediaGameObj(
                    filepath,
                    position=position,
                    velocity=velocity,
                    size=size,
                    loop=loop,
                    audio=audio,
                    object_name=name
                )

                layout.add_object(obj)
                return jsonify({"status": "success"}), 200

            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 400

    def start(self, host=SERVER_IP, port=SERVER_PORT):
        def run_server():
            self.app.run(host=host, port=port, debug=True, use_reloader=False)

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
