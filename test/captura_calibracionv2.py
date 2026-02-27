import cv2
import time
import os
from threading import Thread
from flask import Flask, Response

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
url = 'rtsp://admin:abcd1234@192.168.100.68:554/Stream/Live/102?transportmode=unicast&profile=ONFProfileToken_101'
fps_deseados = 10
intervalo = 1 / fps_deseados
i = 1
modo = 'local'
CARPETA = 'capturas'
DELAY_CAPTURA = 1  # segundos de cuenta atrás antes de guardar

os.makedirs(CARPETA, exist_ok=True)

# -------------------------------
# FLASK PARA MODO WEB
# -------------------------------
app = Flask(__name__)
output_frame = None

def generate_frames():
    global output_frame
    while True:
        if output_frame is None:
            time.sleep(0.01)
            continue
        ret, buffer = cv2.imencode('.jpg', output_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def run_flask():
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

# -------------------------------
# CAPTURA RTSP CON BAJO BUFFER
# -------------------------------
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

countdown_start = None
capturing = False

try:
    if not cap.isOpened():
        print("Error al conectar")
    else:
        print("Todo Correcto")
        print(f"Pulsa 'S' para iniciar cuenta atrás de {DELAY_CAPTURA}s, 'Q' para salir")

        if modo == 'web':
            t = Thread(target=run_flask, daemon=True)
            t.start()

        while True:
            inicio = time.time()

            # Vaciar el buffer interno leyendo frames hasta el más reciente
            for _ in range(3):
                cap.grab()
            ret, frame = cap.retrieve()

            if not ret:
                print("Error al recibir frame")
                break

            frame_pequeno = cv2.resize(frame, (1280, 720))

            if modo == 'local':
                display = frame_pequeno.copy()

                cv2.putText(display, f"Fotos: {i-1}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                if capturing:
                    elapsed = time.time() - countdown_start
                    remaining = DELAY_CAPTURA - elapsed

                    if remaining > 0:
                        cv2.putText(display, f"{int(remaining)+1}", (280, 220),
                                   cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 0, 255), 8)
                        cv2.putText(display, "Coloca el tablero!", (150, 340),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    else:
                        nombre_foto = f"{CARPETA}/captura_{i:03d}.jpg"
                        cv2.imwrite(nombre_foto, frame)
                        print(f"[{i}] Guardada: {nombre_foto}  ({frame.shape[1]}x{frame.shape[0]})")
                        i += 1
                        capturing = False
                        print(f"Pulsa 'S' para la siguiente, 'Q' para salir")

                cv2.imshow('Calibracion - S: iniciar cuenta, Q: salir', display)
                key = cv2.waitKey(30) & 0xFF

                if key == ord('s') and not capturing:
                    capturing = True
                    countdown_start = time.time()
                    print(f"Cuenta atrás de {DELAY_CAPTURA}s iniciada...")

                elif key == ord('q'):
                    print(f"Total fotos guardadas: {i-1}")
                    break

            elif modo == 'web':
                output_frame = frame_pequeno

            tiempo_transcurrido = time.time() - inicio
            if tiempo_transcurrido < intervalo:
                time.sleep(intervalo - tiempo_transcurrido)

finally:
    cap.release()
    if modo == 'local':
        cv2.destroyAllWindows()
        for j in range(1, 5):
            cv2.waitKey(1)
    print("Recursos liberados")
