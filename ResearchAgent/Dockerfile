# 使用官方 Python 3.11 镜像
FROM python:3.11-slim
# 设置工作目录
WORKDIR /app
# 设置环境变量，防止 python 产生 pyc 文件，并确保输出直接打印到控制台
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装系统依赖（如处理某些 python 包需要的构建工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  && rm -rf /var/lib/apt/lists/*
# 拷贝依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 拷贝项目代码
COPY . .
# 暴露 FastAPI 默认端口
EXPOSE 8000
# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]