# localizador_cam_aruco


Paquete ROS 2 para estimar la pose global de una cámara mediante marcadores fiduciarios ArUco.

El nodo se suscribe a las detecciones publicadas por `aruco_opencv`, y para cada marcador visible calcula la pose de la cámara en el frame `map` invirtiendo la transformación relativa cámara-marcador y combinándola con la pose mundial del marcador definida en un archivo YAML. Cuando hay varios marcadores visibles simultáneamente, las estimaciones se fusionan mediante una media ponderada por varianza inversa, asignando mayor peso a los marcadores más cercanos.

## Dependencias

- ROS 2 (Humble / Iron / Rolling)
- [`aruco_opencv`](https://github.com/fictionlab/aruco_opencv) y `aruco_opencv_msgs`
- Python: `numpy`, `scipy`, `cv_bridge`

## Compilación

```bash
cd ~/ros2_ws
colcon build --packages-select localizador_cam_aruco
source install/setup.bash
```

## Configuración

### Mapa de marcadores (`config/aruco_map.yaml`)

Define la pose mundial de cada marcador en el frame `map`. La posición va en metros y los ángulos en grados, usando la convención Roll-Pitch-Yaw (XYZ). Roll/Pitch/Yaw describen hacia dónde apunta la cara del marcador.

```yaml
/localizador_node:
  ros__parameters:
    marker_1: [1.0, 0.0, 1.2, 0.0, 90.0, 90.0]
    marker_2: [0.0, 2.0, 1.2, 0.0, 90.0, 0.0]
```

Referencia rápida de orientaciones habituales:

| La cara del marcador apunta hacia | Roll | Pitch | Yaw  |
|-----------------------------------|------|-------|------|
| +X                                | 0°   | 90°   | 0°   |
| -X                                | 0°   | -90°  | 0°   |
| +Y                                | 0°   | 90°   | 90°  |
| -Y                                | 0°   | 90°   | -90° |
| +Z (techo)                        | 0°   | 180°  | 0°   |
| -Z (suelo)                        | 0°   | 0°    | 0°   |

### Parámetros del tracker (`config/aruco_params.yaml`)

```yaml
/aruco_tracker:
  ros__parameters:
    cam_base_topic: camera/image_raw
    marker_dict: 4X4_50
    marker_size: 0.096        # tamaño del marcador en metros
    image_is_rectified: false
    publish_tf: true
    output_frame: ''
```

## Uso

```bash
ros2 launch localizador_cam_aruco aruco_system.launch.py
```

La pose estimada de la cámara se publica en:

```
/aruco_pose_global  [geometry_msgs/PoseWithCovarianceStamped]
```

## Estructura del paquete

```
localizador_cam_aruco/
├── config/
│   ├── aruco_map.yaml        # poses mundiales de los marcadores
│   └── aruco_params.yaml     # configuración de aruco_opencv
├── launch/
│   └── aruco_system.launch.py
├── localizador_cam_aruco/
│   ├── __init__.py
│   └── localizador_node.py
├── package.xml
├── setup.py
└── setup.cfg
```
