# 使用 Mambaforge 作为基础镜像，它包含了 Conda
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

# 设置工作目录
WORKDIR /app


RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y tzdata && \
    apt-get install -y wget && \
    ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*


RUN wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
   bash /tmp/miniconda.sh -b -p /opt/conda && \
   rm /tmp/miniconda.sh

ENV PATH="/opt/conda/bin:$PATH"

# 配置 Conda 使用清华源
RUN conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/ \
    && conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/ \
    && conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/ \
    && conda config --set show_channel_urls yes \
    && conda clean -i


RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制 requirements.txt 并安装 Python 依赖
# 创建 Conda 环境并指定 Python 版本
RUN conda create -n tts_seed_vc python=3.10 -y

# 激活 Conda 环境
RUN echo "conda activate tts_seed_vc" >> ~/.bashrc
ENV PATH="/opt/conda/envs/tts_seed_vc/bin:$PATH"

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
ENV PYTHONPATH=/app

