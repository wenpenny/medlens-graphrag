FROM python:3.10-slim

WORKDIR /app

# 配置 Debian 国内镜像源（阿里云）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖（使用阿里云 PyPI 镜像）
COPY backend/requirements.txt .
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt

# 预下载 sentence-transformers 模型（使用国内镜像，避免 Hugging Face 超时）
ENV HF_ENDPOINT=https://hf-mirror.com
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# 复制后端代码
COPY backend/ .

# 复制种子数据（DocumentService 在 backend/ 目录下查找 data.json）
COPY data.json ./data.json

# 创建运行时目录
RUN mkdir -p storage/artifacts storage/vectors uploads app/data/seed_documents

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
