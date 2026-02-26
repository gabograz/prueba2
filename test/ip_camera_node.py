#!/usr/bin/env python3
"""
Nodo ROS2 para publicar el stream de una cámara IP via RTSP.
Publica en /camera/image_raw y /camera/camera_info.

Uso:
    python3 ip_camera_node.py

Configurar la URL y la calibración en las variables de la sección CONFIGURACIÓN.
"""

import cv2
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge


# -------------------------------
# CONFIGURACIÓN
# -------------------------------
RTSP_URL = 'rtsp://admin:abcd1234@192.168.100.68:554/Stream/Live/102?transportmode=unicast&profile=ONFProfileToken_101'
CAMERA_INFO_PATH = 'calibration_matrix.yaml'
FPS = 10


class IpCameraNode(Node):
    def __init__(self):
        super().__init__('ip_camera_node')

        self.bridge    = CvBridge()
        self.cam_info_msg = None
        self.resolution   = None

        # QoS
        qos_image = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        qos_info = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.pub_image = self.create_publisher(Image,      '/camera/image_raw',   qos_image)
        self.pub_info  = self.create_publisher(CameraInfo, '/camera/camera_info', qos_info)

        # Conectar cámara
        params = [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000
        ]
        self.cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG, params)

        if not self.cap.isOpened():
            self.get_logger().error(f"No se pudo conectar a la cámara: {RTSP_URL}")
            return

        self.get_logger().info("Cámara IP conectada correctamente.")

        # Leer un frame para obtener la resolución real
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.resolution = (w, h)
            self.get_logger().info(f"Resolución detectada: {w}x{h}")
        else:
            self.resolution = (1280, 720)
            self.get_logger().warn("No se pudo leer el primer frame, usando 1280x720 por defecto.")

        # Cargar calibración ahora que sabemos la resolución
        self.cam_info_msg = self.load_camera_info(CAMERA_INFO_PATH)

        self.timer = self.create_timer(1.0 / FPS, self.publish_frame)

    def load_camera_info(self, path):
        msg = CameraInfo()
        msg.width  = self.resolution[0]
        msg.height = self.resolution[1]
        msg.distortion_model = 'plumb_bob'

        try:
            with open(path, 'r') as f:
                cal = yaml.safe_load(f)

            # camera_matrix es una lista de listas [[fx,0,cx],[0,fy,cy],[0,0,1]]
            k_matrix = cal['camera_matrix']
            k_flat = [float(v) for row in k_matrix for v in row]

            # dist_coeff es una lista de listas [[d0,d1,d2,d3,d4]]
            d_matrix = cal['dist_coeff']
            d_flat = [float(v) for row in d_matrix for v in row]

            fx = k_flat[0]
            fy = k_flat[4]
            cx = k_flat[2]
            cy = k_flat[5]

            msg.k = k_flat
            msg.d = d_flat
            msg.r = [1.0, 0.0, 0.0,
                     0.0, 1.0, 0.0,
                     0.0, 0.0, 1.0]
            msg.p = [fx,  0.0, cx,  0.0,
                     0.0, fy,  cy,  0.0,
                     0.0, 0.0, 1.0, 0.0]

            self.get_logger().info(
                f"Calibración cargada: fx={fx:.1f}, fy={fy:.1f}, cx={cx:.1f}, cy={cy:.1f}"
            )

        except Exception as e:
            self.get_logger().warn(f"No se pudo cargar la calibración: {e}. Publicando sin calibración.")

        return msg

    def publish_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn("Error al leer frame, reintentando...")
            self.cap.open(RTSP_URL)
            return

        now = self.get_clock().now().to_msg()

        img_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        img_msg.header.stamp    = now
        img_msg.header.frame_id = 'camera_optical_frame'
        self.pub_image.publish(img_msg)

        self.cam_info_msg.header.stamp    = now
        self.cam_info_msg.header.frame_id = 'camera_optical_frame'
        self.pub_info.publish(self.cam_info_msg)


def main(args=None):
    rclpy.init(args=args)
    node = IpCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cap.release()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
