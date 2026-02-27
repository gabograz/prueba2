import cv2
import os
import time
from threading import Thread

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
url = 'rtsp://admin:abcd1234@192.168.100.68:554/Stream/Live/102?transportmode=unicast&profile=ONFProfileToken_101'
CARPETA = 'capturas'
os.makedirs(CARPETA, exist_ok=True)

# -------------------------------
# HILO DE CAPTURA CONTINUA
# -------------------------------
frame_actual = None
running = True

def captura_loop():
    global frame_actual, running
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Error al conectar con la cámara")
        running = False
        return

    print("Cámara conectada.")
    while running:
        for _ in range(3):
            cap.grab()
        ret, frame = cap.retrieve()
        if ret:
            frame_actual = frame

    cap.release()

# Lanzar hilo de captura
t = Thread(target=captura_loop, daemon=True)
t.start()

# Esperar a que llegue el primer frame
print("Conectando...")
while frame_actual is None and running:
    time.sleep(0.1)

if not running:
    exit()

# -------------------------------
# BUCLE PRINCIPAL - TECLADO
# -------------------------------
i = 1
print(f"Listo. Pulsa ENTER para guardar foto, 'q' + ENTER para salir.")
print(f"Las fotos se guardan en '{CARPETA}/'")

try:
    while True:
        key = input()

        if key.lower() == 'q':
            print(f"Total fotos guardadas: {i-1}")
            break

        if frame_actual is not None:
            nombre = f"{CARPETA}/captura_{i:03d}.jpg"
            cv2.imwrite(nombre, frame_actual)
            h, w = frame_actual.shape[:2]
            print(f"[{i}] Guardada: {nombre}  ({w}x{h})")
            i += 1
        else:
            print("Sin frame disponible, reintenta")

finally:
    running = False
