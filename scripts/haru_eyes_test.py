import requests
import time
import math

SERVER_URL = "http://localhost:8000"
VIDEO1_NAME = "video1"
VIDEO2_NAME = "video2"

RADIUS = 50
FPS = 30
DURATION = 2.0  # segundos por vuelta

# Nuevo cálculo de centros: restamos el radio al punto extremo deseado
CENTER_POSITIONS = {
    VIDEO1_NAME: (100 - RADIUS, 50),
    VIDEO2_NAME: (500 - RADIUS, 50),
}


def move_to(name, x, y):
    res = requests.post(f"{SERVER_URL}/media/set_position", json={
        "name": name,
        "x": int(x),
        "y": int(y)
    })
    res.raise_for_status()


def do_circle(name, clockwise=True):
    print(f"Moviendo {name} en círculo {'horario' if clockwise else 'antihorario'}")
    cx, cy = CENTER_POSITIONS[name]
    frames = int(FPS * DURATION)
    for i in range(frames):
        t = i / frames * 2 * math.pi
        if not clockwise:
            t = -t
        x = cx + RADIUS * math.cos(t)
        y = cy + RADIUS * math.sin(t)
        move_to(name, x, y)
        time.sleep(1 / FPS)
    print(f"Finalizó movimiento circular de {name}")


def return_to_origin(name):
    x, y = CENTER_POSITIONS[name]
    move_to(name, x + RADIUS, y)  # punto extremo derecho
    print(f"{name} volvió a su posición original")


def main():
    while True:
        cmd = input("Comando [circle1, circle2, acircle1, acircle2, reset1, reset2, quit]: ").strip()
        if cmd == "quit":
            break
        elif cmd == "circle1":
            do_circle(VIDEO1_NAME, clockwise=True)
        elif cmd == "acircle1":
            do_circle(VIDEO1_NAME, clockwise=False)
        elif cmd == "reset1":
            return_to_origin(VIDEO1_NAME)
        elif cmd == "circle2":
            do_circle(VIDEO2_NAME, clockwise=True)
        elif cmd == "acircle2":
            do_circle(VIDEO2_NAME, clockwise=False)
        elif cmd == "reset2":
            return_to_origin(VIDEO2_NAME)
        else:
            print("Comando no reconocido")


if __name__ == "__main__":
    main()
