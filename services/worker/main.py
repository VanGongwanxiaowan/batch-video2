import sys
from pathlib import Path

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.main", log_to_file=False)

def main() -> None:
    logger.info("Hello from worker!")


if __name__ == "__main__":
    main()
