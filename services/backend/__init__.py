"""Backend服务模块"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径，以便导入core模块
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

__all__ = []

