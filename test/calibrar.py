import os

import cv2
import numpy as np
import glob
import yaml

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
TABLERO = (7, 7)          # intersecciones interiores
TAMANO_CUADRADO = 0.02    # 2cm en metros
CARPETA = 'capturas'

# -------------------------------
# PREPARACIÓN
# -------------------------------

EXCLUIR = ['captura_010.jpg', 'captura_016.jpg', 'captura_017.jpg', 
           'captura_018.jpg', 'captura_019.jpg', 'captura_020.jpg', 'captura_021.jpg']

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objp = np.zeros((TABLERO[0] * TABLERO[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:TABLERO[0], 0:TABLERO[1]].T.reshape(-1, 2)
objp *= TAMANO_CUADRADO

obj_points = []
img_points = []

fotos = sorted(glob.glob(f'{CARPETA}/*.jpg'))
print(f"Fotos encontradas: {len(fotos)}")

# -------------------------------
# DETECCIÓN DE ESQUINAS
# -------------------------------
fotos_validas = 0
fotos_fallidas = []

for fname in fotos:
    if os.path.basename(fname) in EXCLUIR:
        print(f"  SKIP: {fname}")
        continue
    img = cv2.imread(fname)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, TABLERO, None)

    if ret:
        obj_points.append(objp)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        img_points.append(corners2)
        fotos_validas += 1
        print(f"  OK: {fname}")
    else:
        fotos_fallidas.append(fname)
        print(f"  FAIL: {fname} — tablero no detectado")

print(f"\nFotos válidas: {fotos_validas}/{len(fotos)}")

if fotos_validas < 10:
    print("ERROR: pocas fotos válidas, necesitas al menos 10. Toma más fotos.")
    exit()

# -------------------------------
# CALIBRACIÓN
# -------------------------------
h, w = cv2.imread(fotos[0]).shape[:2]
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    obj_points, img_points, (w, h), None, None)

print(f"\nError de reproyección: {ret:.4f} px")
if ret < 0.5:
    print("Excelente calibración")
elif ret < 1.0:
    print("Buena calibración")
else:
    print("Calibración mejorable — considera tomar más fotos con más variedad de posiciones")

print(f"\nMatriz de cámara:")
print(f"  fx={K[0,0]:.2f}, fy={K[1,1]:.2f}")
print(f"  cx={K[0,2]:.2f}, cy={K[1,2]:.2f}")
print(f"\nCoeficientes de distorsión:")
print(f"  {dist.tolist()}")

# -------------------------------
# GUARDAR
# -------------------------------
calibracion = {
    'camera_matrix': K.tolist(),
    'dist_coeff': dist.tolist(),
    'image_width': w,
    'image_height': h,
    'zoom_ratio': 1,
}

# Después de calibrar, calcular error por foto
for i, (objp_i, imgp_i, rvec, tvec) in enumerate(zip(obj_points, img_points, rvecs, tvecs)):
    imgpoints_repr, _ = cv2.projectPoints(objp_i, rvec, tvec, K, dist)
    error = cv2.norm(imgp_i, imgpoints_repr, cv2.NORM_L2) / len(imgpoints_repr)
    print(f"  {fotos[i]}: {error:.4f} px")

with open('calibration_matrix.yaml', 'w') as f:
    yaml.dump(calibracion, f, default_flow_style=False)

print(f"\nCalibración guardada en calibration_matrix.yaml")
print(f"Resolución: {w}x{h}")
