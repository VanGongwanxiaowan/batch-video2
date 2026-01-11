#!/bin/bash

# BatchShort1 Backend 服务启动脚本
# 服务已迁移到 services/backend/ 目录

# 进入 backend 目录
cd "$(dirname "$0")"

# 检查并安装依赖
# if [ -f "requirements.txt" ]; then
#     echo "Installing dependencies from requirements.txt..."
#     pip install -r requirements.txt
#     if [ $? -ne 0 ]; then
#         echo "Failed to install dependencies. Exiting."
#         exit 1
#     fi
#     echo "Dependencies installed."
# fi

# 启动 gunicorn
# -w: worker 数量，这里设置为4，可以根据服务器CPU核心数调整
# -b: 绑定地址和端口，与 main.py 中的 uvicorn 端口一致
# main:app: 指定 main 模块中的 app 对象
# --daemon: 后台运行
# --log-file: gunicorn 日志文件
# --access-logfile: gunicorn 访问日志文件
# --error-logfile: gunicorn 错误日志文件
# --pid: pid 文件，用于停止服务
nohup gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8006 api_main:app &
echo "Gunicorn server started. Check gunicorn.log for details."