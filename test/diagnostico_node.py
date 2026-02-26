#!/usr/bin/env python3
"""
Nodo de diagnóstico para verificar las detecciones de aruco_opencv.
Muestra por consola el ID, distancia y pose de cada marcador detectado,
sin hacer ninguna conversión al frame del mapa.

Uso:
    python3 diagnostico_node.py
"""

import rclpy
from rclpy.node import Node
from aruco_opencv_msgs.msg import ArucoDetection
import numpy as np


class DiagnosticoNode(Node):
    def __init__(self):
        super().__init__('diagnostico_node')

        self.subscription = self.create_subscription(
            ArucoDetection,
            '/aruco_detections',
            self.callback,
            10
        )
        self.get_logger().info("Diagnóstico iniciado, esperando detecciones...")

    def callback(self, msg):
        if not msg.markers:
            return

        print(f"\n{'='*50}")
        print(f"Frame: {msg.header.frame_id} | Marcadores: {len(msg.markers)}")
        print(f"{'='*50}")

        for marker in msg.markers:
            p = marker.pose.position
            q = marker.pose.orientation

            # Distancia euclidea cámara → marcador
            distancia = np.sqrt(p.x**2 + p.y**2 + p.z**2)

            # Descomposición de la pose
            # p.z es la distancia frontal (profundidad)
            # p.x es el desplazamiento lateral (derecha/izquierda)
            # p.y es el desplazamiento vertical (arriba/abajo)
            print(f"\n  Marcador ID: {marker.marker_id}")
            print(f"  Distancia total:    {distancia:.4f} m")
            print(f"  Profundidad (Z):    {p.z:.4f} m")
            print(f"  Lateral    (X):     {p.x:+.4f} m  ({'derecha' if p.x > 0 else 'izquierda'})")
            print(f"  Vertical   (Y):     {p.y:+.4f} m  ({'abajo' if p.y > 0 else 'arriba'})")
            print(f"  Orientación (quat): x={q.x:.3f}  y={q.y:.3f}  z={q.z:.3f}  w={q.w:.3f}")


def main(args=None):
    rclpy.init(args=args)
    node = DiagnosticoNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
