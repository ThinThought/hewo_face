import threading
from flask import Flask, request, jsonify

SERVER_IP = '0.0.0.0'
SERVER_PORT = 8000


class ServerEndPoint:
    def __init__(self, main_window):
        self.app = Flask(__name__)
        self.main_window = main_window
        self.setup_routes()

    def get_layout(self):
        if self.main_window.active_layout is not None:
            return self.main_window.layout_dict[self.main_window.active_layout]
        return None



    def setup_routes(self):
        @self.app.route('/set_layout', methods=['POST'])
        def set_layout():
            data = request.get_json()
            name = data.get("name")
            if name not in self.main_window.layout_dict:
                return jsonify({"status": "error", "message": f"Layout '{name}' not found"}), 404

            self.main_window.active_layout = name
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
            layout = self.get_layout()
            layout.toggle_talk()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/trigger_blink', methods=['POST'])
        def trigger_blink():
            layout = self.get_layout()
            layout.trigger_blink()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/adjust_position', methods=['POST'])
        def adjust_position():
            layout = self.get_layout()
            data = request.get_json()
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            layout.adjust_position(dx, dy)
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/set_size', methods=['POST'])
        def adjust_size():
            layout = self.get_layout()
            data = request.get_json()
            size = int(data.get("value", 0))
            layout.set_face_size(size)
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/set_random_emotion', methods=['POST'])
        def set_random_emotion():
            layout = self.get_layout()
            layout.set_random_emotion()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/reset_emotion', methods=['POST'])
        def reset_emotion():
            layout = self.get_layout()
            layout.reset_emotion()
            return jsonify({"status": "success"}), 200

        @self.app.route('/hewo/adjust_emotion/<param>', methods=['POST'])
        def adjust_emotion(param):
            layout = self.get_layout()
            data = request.get_json()
            try:
                value = int(data.get("value"))
            except (TypeError, ValueError):
                return jsonify({"status": "error", "message": "Missing or invalid 'value' (must be int)"}), 400

            layout.adjust_emotion(param, value)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/move', methods=['POST'])
        def move_media():
            layout = self.get_layout()
            data = request.get_json()
            name = data.get("name")
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            layout.move_object(name, dx, dy)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/set_position', methods=['POST'])
        def set_position():
            layout = self.get_layout()
            data = request.get_json()
            name = data.get("name")
            x = int(data.get("x", 0))
            y = int(data.get("y", 0))
            layout.set_position(name, x, y)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/pause', methods=['POST'])
        def pause_media():
            layout = self.get_layout()
            data = request.get_json()
            name = data.get("name")
            layout.pause_object(name)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/play', methods=['POST'])
        def play_media():
            layout = self.get_layout()
            data = request.get_json()
            name = data.get("name")
            layout.play_object(name)
            return jsonify({"status": "success"}), 200

        @self.app.route('/media/remove', methods=['POST'])
        def remove_media():
            layout = self.get_layout()
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
