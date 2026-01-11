import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("image_gen.ai_image_gen.consumer_worker.test", log_to_file=False)

GENERATED_IMAGES_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + "/generated_images"
logger.debug(f"GENERATED_IMAGES_DIR: {GENERATED_IMAGES_DIR}")