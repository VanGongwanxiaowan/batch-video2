#!/bin/bash

# BatchShort1 Worker 服务启动脚本
# 服务已迁移到 services/worker/ 目录

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 进入 worker 目录
cd "$SCRIPT_DIR"

# 检查虚拟环境是否存在
if [ -d "$PROJECT_ROOT/.venv" ]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# 停止已运行的 worker_main 进程
echo "🔍 检查是否有运行中的 worker_main 进程..."
if pgrep -f "worker_main.py" > /dev/null; then
    echo "⚠️  发现运行中的 worker_main 进程，正在停止..."
    pkill -f "worker_main.py"
    sleep 2
fi

# 启动 worker_main
echo "🚀 启动 worker_main..."
echo "   使用 Python: $PYTHON_CMD"
echo "   工作目录: $SCRIPT_DIR"
echo "   日志文件: $SCRIPT_DIR/worker.log"

# 使用 nohup 后台运行
nohup "$PYTHON_CMD" worker_main.py > worker.log 2>&1 &

# 等待一秒确保进程启动
sleep 1

# 检查进程是否启动成功
if pgrep -f "worker_main.py" > /dev/null; then
    PID=$(pgrep -f "worker_main.py")
    echo "✅ worker_main 启动成功！"
    echo "   PID: $PID"
    echo "   查看日志: tail -f $SCRIPT_DIR/worker.log"
    echo "   停止进程: pkill -f worker_main.py"
else
    echo "❌ worker_main 启动失败，请查看日志:"
    echo "   tail -n 50 $SCRIPT_DIR/worker.log"
    exit 1
fi

