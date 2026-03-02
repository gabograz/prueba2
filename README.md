# localizador_cam_aruco

Paquete ROS 2 para estimar la pose global de un robot mediante marcadores fiduciarios ArUco.

El nodo se suscribe a las detecciones publicadas por `aruco_opencv`, y para cada marcador visible calcula la pose de la cámara en el frame `map` invirtiendo la transformación relativa cámara-marcador y combinándola con la pose mundial del marcador definida en un archivo YAML. Opcionalmente, si se proporciona la posición de la cámara respecto al robot, se obtiene directamente la pose de `base_link` en el mapa. Cuando hay varios marcadores visibles simultáneamente, las estimaciones se fusionan mediante una media ponderada por varianza inversa, asignando mayor peso a los marcadores más cercanos.

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
| +X                                | 90°  | 0°    | 90°  |
| -X                                | 90°  | 0°    | -90° |
| +Y                                | 90°  | 0°    | 180° |
| -Y                                | 90°  | 0°    | 0°   |
| +Z (techo)                        | 0°   | 0°    | 0°   |
| -Z (suelo)                        | 180° | 0°    | 0°   |

### Parámetros del tracker (`config/aruco_params.yaml`)

```yaml
/aruco_tracker:
  ros__parameters:
    cam_base_topic: camera/image_raw
    marker_dict: 4X4_50       #Diccionario
    marker_size: 0.096        #Tamaño del marcador en metros
    image_is_rectified: false
    publish_tf: true
    output_frame: ''
```

### Configuración del robot (`config/robot_config.yaml`)

Define la posición y orientación de la cámara respecto al centro del robot. Si no se define, el nodo asume que la cámara está en el centro del robot.

> **Importante:** los ejes X, Y, Z de este parámetro están expresados en el **frame de la cámara**, no en el de `base_link`:
>
> | Eje | Dirección física |
> |-----|-----------------|
> | X   | Izquierda de la cámara |
> | Y   | arriba de la cámara |
> | Z   | adelante de la cámara |

```yaml
/localizador_node:
  ros__parameters:
    # [X, Y, Z, Roll, Pitch, Yaw] — metros y grados
    # Ejemplo: cámara 30cm por delante del centro del robot, sin rotación
    camera_to_base: [0.0, 0.0, 0.3, 0.0, 0.0, 0.0]
```

## Puesta en marcha paso a paso

### 1. Medir y colocar los marcadores

Coloca los marcadores ArUco en posiciones fijas del entorno. Mide con cinta métrica la posición de cada uno respecto al origen del mapa `[0, 0, 0]`.

### 2. Configurar `aruco_map.yaml`

Para cada marcador, añade una entrada con su posición `[X, Y, Z]` en metros y su orientación `[Roll, Pitch, Yaw]` en grados. Usa la tabla de orientaciones de la sección anterior para saber qué ángulos corresponden a la dirección a la que mira la cara del marcador.

```yaml
/localizador_node:
  ros__parameters:
    marker_0: [1.0, 0.0, 1.2, 90.0, 0.0, 90.0]   # mira hacia +X
    marker_1: [0.0, 2.0, 1.2, 90.0, 0.0, 180.0]  # mira hacia +Y
```

### 3. Verificar cada marcador

Arranca el nodo y coloca el robot en una posición conocida frente a cada marcador. Comprueba que la pose publicada en `/robot_pose_global` coincide con la posición real del robot:

```bash
ros2 topic echo /robot_pose_global
```

Si la posición no es correcta, revisa la orientación del marcador en el YAML.

### 4. Configurar `robot_config.yaml`

Mide la distancia de la cámara al centro del robot **en ejes de la cámara**  y ponla en `camera_to_base`:

```yaml
camera_to_base: [0.0, 0.0, 0.3, 0.0, 0.0, 0.0]  # 30cm por delante
```

Para verificarlo, coloca el robot en una posición conocida y comprueba que el offset se aplica correctamente en la pose publicada.

## Uso

```bash
ros2 launch localizador_cam_aruco aruco_system.launch.py
```

La pose estimada del robot se publica en:

```
/robot_pose_global  [geometry_msgs/PoseWithCovarianceStamped]
```

## Estructura del paquete

```
localizador_cam_aruco/
├── config/
│   ├── aruco_map.yaml        # poses mundiales de los marcadores
│   ├── aruco_params.yaml     # configuración de aruco_opencv
│   └── robot_config.yaml     # posición de la cámara en el robot
├── launch/
│   └── aruco_system.launch.py
├── localizador_cam_aruco/
│   ├── __init__.py
│   └── localizador_node.py
├── package.xml
├── setup.py
└── setup.cfg
```

## Topics y nodos

### aruco_tracker (aruco_opencv)

Suscrito a:
- `/camera/image_raw` — `sensor_msgs/msg/Image`
- `/camera/camera_info` — `sensor_msgs/msg/CameraInfo`

Publica en:
- `/aruco_detections` — `aruco_opencv_msgs/msg/ArucoDetection`
- `/aruco_tracker/debug` — `sensor_msgs/msg/Image`
- `/tf` — `tf2_msgs/msg/TFMessage`

### localizador_node

Suscrito a:
- `/aruco_detections` — `aruco_opencv_msgs/msg/ArucoDetection`

Publica en:
- `/robot_pose_global` — `geometry_msgs/msg/PoseWithCovarianceStamped`