import cv2
import time
from threading import Thread

# Para el modo servidor web
from flask import Flask, Response

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
params = [
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000
]

url = 'rtsp://admin:abcd1234@192.168.100.68:554/Stream/Live/102?transportmode=unicast&amp;profile=ONFProfileToken_101'
fps_deseados = 10
intervalo = 1 / fps_deseados
i = 5

# Modo: 'local' = cv2.imshow, 'web' = servidor Flask
modo = 'web'
modo = 'local'

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
        # Codifica en JPEG para enviar al navegador
        ret, buffer = cv2.imencode('.jpg', output_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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

        # Si estamos en modo web, lanzamos Flask en hilo aparte
        if modo == 'web':
            t = Thread(target=run_flask, daemon=True)
            t.start()
            print("Servidor web iniciado en http://localhost:5000/video_feed")

        while True:
            inicio = time.time()
            ret, frame = cap.read()
            if not ret:
                print("Error al recibir frame")
                break

            # Reducimos tamaño para mostrar / web
            frame_pequeno = cv2.resize(frame, (640, 360))

            if modo == 'local':
                cv2.imshow('Sowze Live View', frame_pequeno)
                key = cv2.waitKey(30) & 0xFF

                if key == ord('s'):
                    nombre_foto = f"captura_{i}.jpg"
                    i += 1
                    cv2.imwrite(nombre_foto, frame)
                    print(f"Foto guardada como {nombre_foto}")

                elif key == ord('q'):
                    print("Cerrando programa...")
                    break
            elif modo == 'web':
                # Solo actualizamos el frame global
                output_frame = frame_pequeno

            # Control de FPS
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
