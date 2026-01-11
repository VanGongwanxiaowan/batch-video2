FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y \
        curl \
        tzdata \
        wget \
        && \
    ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# 安装 Miniconda
RUN wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh

ENV PATH="/opt/conda/bin:$PATH"

# 配置 Conda 使用清华源
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/ && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ && \
    conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ && \
    conda config --set show_channel_urls yes && \
    conda clean -i

# 安装 Python 3.10 和 ffmpeg
RUN conda install python=3.10 ffmpeg -y

# 配置 Pip 使用清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用程序代码
COPY . .

# 暴露 FastAPI 端口
EXPOSE 6016

# 定义启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6016"]
