# FROM python:3.9.22-slim
FROM crpi-oge0xe9byb7l546u.cn-shanghai.personal.cr.aliyuncs.com/pandaai/offline_workflow_service:latest
ENV TZ=Asia/Shanghai

WORKDIR /app

# 复制项目文件
COPY . /app/

# 安装项目及其依赖
RUN pip install -e .

# 暴露服务端口
EXPOSE 8000

# 默认 worker 数量，可通过环境变量覆盖
ENV PANDA_SERVER_WORKERS=4

# 使用uvicorn启动服务，从环境变量 WORKERS 读取 worker 数量
CMD ["sh", "-c", "uvicorn panda_server.main:app --host 0.0.0.0 --port 8000 --workers $PANDA_SERVER_WORKERS"]
