import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_name = 'localizador_cam_aruco'
    pkg_share_dir = get_package_share_directory(pkg_name)

    aruco_map_path    = os.path.join(pkg_share_dir, 'config', 'aruco_map.yaml')
    aruco_params_path = os.path.join(pkg_share_dir, 'config', 'aruco_params.yaml')
    robot_config_path = os.path.join(pkg_share_dir, 'config', 'robot_config.yaml')

    aruco_tracker_node = Node(
        package='aruco_opencv',
        executable='aruco_tracker_autostart',
        name='aruco_tracker',
        parameters=[aruco_params_path],
        output='screen'
    )

    localizador_node = Node(
        package=pkg_name,
        executable='localizador_node',
        name='localizador_node',
        parameters=[aruco_map_path, robot_config_path],
        output='screen'
    )

    return LaunchDescription([
        aruco_tracker_node,
        localizador_node
    ])
