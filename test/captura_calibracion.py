import cv2
import time
import os
from threading import Thread
from flask import Flask, Response

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
params = [
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000
]

url = 'rtsp://admin:abcd1234@192.168.100.68:554/Stream/Live/102?transportmode=unicast&profile=ONFProfileToken_101'
fps_deseados = 10
intervalo = 1 / fps_deseados
i = 1
modo = 'local'
CARPETA = 'capturas'

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
# CAPTURA RTSP
# -------------------------------
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG, params)

try:
    if not cap.isOpened():
        print("Error al conectar")
    else:
        print("Todo Correcto")
        print("Pulsa 'S' para guardar foto, 'Q' para salir")

        if modo == 'web':
            t = Thread(target=run_flask, daemon=True)
            t.start()
            print("Servidor web iniciado en http://localhost:8080/video_feed")

        while True:
            inicio = time.time()
            ret, frame = cap.read()
            if not ret:
                print("Error al recibir frame")
                break

            frame_pequeno = cv2.resize(frame, (1080, 720))

            if modo == 'local':
                # Mostrar contador de fotos en pantalla
                cv2.putText(frame_pequeno, f"Fotos: {i-1}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow('Calibracion - S: guardar, Q: salir', frame_pequeno)
                key = cv2.waitKey(30) & 0xFF

                if key == ord('s'):
                    # Guardar en resolución original, no la reducida
                    nombre_foto = f"{CARPETA}/captura_{i:03d}.jpg"
                    cv2.imwrite(nombre_foto, frame)
                    print(f"[{i}] Guardada: {nombre_foto}  ({frame.shape[1]}x{frame.shape[0]})")
                    i += 1

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
