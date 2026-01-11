# HeyGem Digital Human Integration

This directory contains the production-ready integration of the [HeyGem-Linux-Python-Hack](https://github.com/Holasyb918/HeyGem-Linux-Python-Hack) project.

## Setup Instructions

To make the local inference work, you need to copy the necessary model files and libraries from the original repository.

1.  **Clone the original repository**:
    ```bash
    git clone https://github.com/Holasyb918/HeyGem-Linux-Python-Hack.git
    ```

2.  **Copy Library Files**:
    Copy the `.so` file (e.g., `preprocess_audio_and_3dmm.cpython-38-x86_64-linux-gnu.so`) to `services/worker/services/digital_human/heygem/libs/`.
    
    ```bash
    cp HeyGem-Linux-Python-Hack/*.so services/worker/services/digital_human/heygem/libs/
    ```

3.  **Copy Python Modules**:
    Copy the helper modules (`face_attr_detect`, `face_detect_utils`, `face_lib`, `h_utils`) to `services/worker/services/digital_human/heygem/libs/`.

    ```bash
    cp -r HeyGem-Linux-Python-Hack/face_* services/worker/services/digital_human/heygem/libs/
    cp -r HeyGem-Linux-Python-Hack/h_utils services/worker/services/digital_human/heygem/libs/
    ```

4.  **Copy Models**:
    Download the required models (check `download.sh` in the original repo) and place them in `services/worker/services/digital_human/heygem/models/`.

    ```bash
    # Example structure
    # services/worker/services/digital_human/heygem/models/
    #   ├── check_points/
    #   ├── face_detection/
    #   └── ...
    ```

## Usage

The `HeyGemInferenceEngine` class wraps the complexity of the original script into a clean, thread-safe Python API.

```python
from services.worker.services.digital_human.heygem import HeyGemInferenceEngine

engine = HeyGemInferenceEngine()
output_path = engine.generate(
    video_path="path/to/template.mp4",
    audio_path="path/to/audio.mp3",
    output_path="path/to/output.mp4"
)
```

## Optimization Features

*   **Singleton Initialization**: Models are loaded only once.
*   **GPU Acceleration**: Automatically detects CUDA and uses it if available.
*   **Production Logging**: Integrated with the system's logging framework.
*   **Async Processing**: Ready for integration with asynchronous pipelines.
