#!/bin/bash
# ============================================================================
# BatchShort Celery Worker 启动脚本
# ============================================================================
# 用于启动 Celery Worker、Beat 和 Flower 监控
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    echo -e "${GREEN}加载环境变量: .env${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${YELLOW}警告: .env 文件不存在，使用默认配置${NC}"
fi

# 默认参数
COMMAND="${1:-worker}"
CONCURRENCY="${WORKER_CONCURRENCY:-1}"
LOGLEVEL="${LOG_LEVEL:-info}"
FLOWER_PORT="${FLOWER_PORT:-5555}"

# 显示帮助信息
show_help() {
    cat << EOF
BatchShort Celery Worker 启动脚本

用法: $0 [COMMAND] [OPTIONS]

命令:
  worker      启动 Celery Worker (默认)
  beat        启动 Celery Beat 调度器
  flower      启动 Flower 监控界面
  all         启动所有服务 (worker + beat + flower)

选项:
  --concurrency N   Worker 并发数 (默认: 1)
  --port N          Flower 服务端口 (默认: 5555)
  --loglevel L      日志级别 (默认: info)
  --help            显示此帮助信息

示例:
  $0 worker                    # 启动 Worker
  $0 worker --concurrency 2    # 启动 Worker，并发数为 2
  $0 beat                      # 启动 Beat 调度器
  $0 flower --port 5555        # 启动 Flower 监控
  $0 all                       # 启动所有服务

环境变量:
  WORKER_CONCURRENCY           Worker 并发数
  LOG_LEVEL                    日志级别
  FLOWER_PORT                  Flower 端口
  CELERY_BROKER_URL           Celery Broker URL
  CELERY_RESULT_BACKEND       Celery Result Backend

EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --port)
            FLOWER_PORT="$2"
            shift 2
            ;;
        --loglevel)
            LOGLEVEL="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            COMMAND="$1"
            shift
            ;;
    esac
done

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo -e "${RED}错误: Python 未安装${NC}"
    exit 1
fi

# 检查依赖
echo -e "${GREEN}检查依赖...${NC}"
python -c "import celery" 2>/dev/null || {
    echo -e "${RED}错误: Celery 未安装${NC}"
    echo "请运行: pip install celery"
    exit 1
}

# 显示配置信息
echo -e "${GREEN}=== BatchShort Celery 配置 ===${NC}"
echo "命令: $COMMAND"
echo "并发数: $CONCURRENCY"
echo "日志级别: $LOGLEVEL"
echo "Broker: ${CELERY_BROKER_URL:-redis://localhost:6379/0}"
echo "Backend: ${CELERY_RESULT_BACKEND:-redis://localhost:6379/1}"
echo "Flower 端口: $FLOWER_PORT"
echo ""

# 启动函数
start_worker() {
    echo -e "${GREEN}启动 Celery Worker...${NC}"
    cd services/worker
    exec python worker_main.py worker \
        --concurrency="$CONCURRENCY" \
        --loglevel="$LOGLEVEL"
}

start_beat() {
    echo -e "${GREEN}启动 Celery Beat...${NC}"
    cd services/worker
    exec python worker_main.py beat \
        --loglevel="$LOGLEVEL"
}

start_flower() {
    echo -e "${GREEN}启动 Flower 监控 (端口: $FLOWER_PORT)...${NC}"
    cd services/worker
    exec python worker_main.py flower \
        --port="$FLOWER_PORT"
}

# 根据命令启动服务
case "$COMMAND" in
    worker)
        start_worker
        ;;
    beat)
        start_beat
        ;;
    flower)
        start_flower
        ;;
    all)
        echo -e "${YELLOW}启动所有服务...${NC}"
        echo -e "${YELLOW}注意: 使用 tmux 或 screen 来运行多个服务${NC}"

        # 在后台启动各个服务
        start_worker &
        WORKER_PID=$!

        sleep 2
        start_beat &
        BEAT_PID=$!

        sleep 2
        start_flower &
        FLOWER_PID=$!

        echo -e "${GREEN}所有服务已启动${NC}"
        echo "Worker PID: $WORKER_PID"
        echo "Beat PID: $BEAT_PID"
        echo "Flower PID: $FLOWER_PID"
        echo ""
        echo "访问 Flower: http://localhost:$FLOWER_PORT"
        echo ""
        echo "按 Ctrl+C 停止所有服务"

        # 等待所有后台进程
        trap "kill $WORKER_PID $BEAT_PID $FLOWER_PID 2>/dev/null; echo -e '${RED}所有服务已停止${NC}'; exit 0" INT TERM

        wait
        ;;
    *)
        echo -e "${RED}错误: 未知命令 '$COMMAND'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
