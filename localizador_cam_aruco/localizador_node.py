import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
from aruco_opencv_msgs.msg import ArucoDetection

import numpy as np
from scipy.spatial.transform import Rotation as R


class ArucoLocalizer(Node):
    """
    Nodo de localización global basado en marcadores ArUco.

    Estima la pose del robot en el frame 'map' a partir de las detecciones
    publicadas por aruco_opencv. Para cada marcador visible, invierte la pose
    relativa cámara-marcador y la combina con la pose mundial del marcador
    (definida en aruco_map.yaml) para obtener la pose de la cámara en el mapa.
    Opcionalmente, si se define camera_to_base en robot_config.yaml, se aplica
    el transform cámara→base_link para obtener la pose del robot.

    Cuando hay varios marcadores visibles simultáneamente, las estimaciones se
    fusionan mediante una media ponderada por varianza inversa, asignando mayor
    peso a los marcadores más cercanos.

    Parámetros (aruco_map.yaml):
        marker_<id>: [X, Y, Z, Roll, Pitch, Yaw]
            Pose mundial de cada marcador en metros y grados.

    Parámetros (robot_config.yaml):
        camera_to_base: [X, Y, Z, Roll, Pitch, Yaw]
            Pose de la cámara respecto a base_link en metros y grados.
            Si no se define, se asume que la cámara está en el centro del robot.
    """

    def __init__(self):
        super().__init__(
            'localizador_node',
            allow_undeclared_parameters=True,
            automatically_declare_parameters_from_overrides=True
        )
        self.get_logger().info("Localizador iniciado, cargando mapa de marcadores...")

        # Rotación OpenCV → ROS
        self.R_opencv_to_ros = R.from_matrix([
            [ 0, -1,  0],
            [ 0,  0, -1],
            [ 1,  0,  0]
        ])

        # Leer transform cámara → base_link desde robot_config.yaml.
        # Si no está definido se usa la identidad (cámara en el centro del robot).
        if self.has_parameter('camera_to_base'):
            ctb = self.get_parameter('camera_to_base').value
            self.t_cam_to_base   = np.array(ctb[:3])
            self.rot_cam_to_base = R.from_euler('xyz', np.radians(ctb[3:]))
            self.get_logger().info(
                f"Transform cámara→base_link cargado: "
                f"T={self.t_cam_to_base}, RPY={ctb[3:]}°"
            )
        else:
            self.t_cam_to_base   = np.zeros(3)
            self.rot_cam_to_base = R.identity()
            self.get_logger().info(
                "camera_to_base no definido, se asume cámara en el centro del robot."
            )

        self.subscription = self.create_subscription(
            ArucoDetection,
            '/aruco_detections',
            self.aruco_callback,
            10
        )

        self.publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            '/robot_pose_global',
            10
        )

    def aruco_callback(self, msg):
        if not msg.markers:
            return

        sum_pos      = np.zeros(3)
        sum_q_matrix = np.zeros((4, 4))
        sum_weights  = 0.0

        for marker in msg.markers:
            marker_id  = marker.marker_id
            param_name = f'marker_{marker_id}'

            if not self.has_parameter(param_name):
                continue

            coords = self.get_parameter(param_name).value
            if len(coords) < 6:
                self.get_logger().warn(
                    f"Marcador {marker_id}: se esperan 6 valores [X,Y,Z,Roll,Pitch,Yaw] "
                    f"en el YAML pero hay {len(coords)}."
                )
                continue

            # Pose mundial del marcador
            marker_pos_world = np.array(coords[:3])
            rot_marker_world = R.from_euler('xyz', np.radians(coords[3:]))

            # aruco_opencv nos da la pose del marcador relativa a la cámara.
            # Necesitamos lo contrario: la pose de la cámara relativa al marcador.
            # Para invertir una pose rígida:
            #   t_inv = -R^T * t
            #   R_inv = R^T
            p = marker.pose.position
            q = marker.pose.orientation
            t_cam_to_marker   = np.array([p.x, p.y, p.z])
            rot_cam_to_marker = R.from_quat([q.x, q.y, q.z, q.w])

            rot_marker_to_cam = rot_cam_to_marker.inv()
            t_marker_to_cam   = rot_marker_to_cam.apply(-t_cam_to_marker)


            # Pose de la cámara en el mapa
            t_in_map      = rot_marker_world.apply(t_marker_to_cam)
            cam_pos       = marker_pos_world + t_in_map
            rot_cam_world = rot_marker_world * rot_marker_to_cam

            # Aplicar transform cámara → base_link para obtener pose del robot
            rot_base_world = rot_cam_world * self.rot_cam_to_base.inv()
            base_pos       = cam_pos + rot_cam_world.apply(self.t_cam_to_base)
            base_quat      = rot_base_world.as_quat()  # [x, y, z, w]

            # Peso inversamente proporcional a la varianza estimada (distancia²)
            distancia = max(np.linalg.norm(t_cam_to_marker), 0.05)
            peso      = 1.0 / (0.01 * distancia ** 2)

            sum_pos      += base_pos * peso
            sum_q_matrix += peso * np.outer(base_quat, base_quat)
            sum_weights  += peso

            self.get_logger().debug(
                f"Marcador {marker_id}: "
                f"pos=({base_pos[0]:.3f}, {base_pos[1]:.3f}, {base_pos[2]:.3f}), "
                f"dist={distancia:.3f}m, peso={peso:.1f}"
            )

        if sum_weights <= 0.0:
            return

        # Media ponderada de posición
        pos_final = sum_pos / sum_weights

        # Media ponderada de orientación (método de Markley):
        # el autovector del mayor autovalor de la matriz acumulada es
        # el cuaternión que minimiza la suma ponderada de distancias angulares
        _, eigenvectors = np.linalg.eigh(sum_q_matrix)
        q_final = eigenvectors[:, -1]
        if q_final[3] < 0:
            q_final = -q_final  # forma canónica: w >= 0

        incertidumbre = 1.0 / sum_weights

        # Construcción del mensaje
        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp    = msg.header.stamp
        pose_msg.header.frame_id = 'map'

        pose_msg.pose.pose.position.x    = float(pos_final[0])
        pose_msg.pose.pose.position.y    = float(pos_final[1])
        pose_msg.pose.pose.position.z    = float(pos_final[2])
        pose_msg.pose.pose.orientation.x = float(q_final[0])
        pose_msg.pose.pose.orientation.y = float(q_final[1])
        pose_msg.pose.pose.orientation.z = float(q_final[2])
        pose_msg.pose.pose.orientation.w = float(q_final[3])

        # Covarianza diagonal 6x6 [x, y, z, roll, pitch, yaw]
        for i in [0, 7, 14, 21, 28, 35]:
            pose_msg.pose.covariance[i] = incertidumbre

        self.publisher.publish(pose_msg)

        rpy = R.from_quat(q_final).as_euler('xyz', degrees=True)
        self.get_logger().info(
            f"X={pos_final[0]:.3f}  Y={pos_final[1]:.3f}  Z={pos_final[2]:.3f} | "
            f"R={rpy[0]:.1f}°  P={rpy[1]:.1f}°  Y={rpy[2]:.1f}°  "
            f"(σ²={incertidumbre:.4f})"
        )


def main(args=None):
    rclpy.init(args=args)
    node = ArucoLocalizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
