#!/bin/bash
# 一键构建并部署AI-CodeReview Docker镜像（Linux环境）
set -e
IMAGE_NAME=ai-codereview:latest
CONTAINER_NAME=ai-codereview

# 构建镜像
echo "[1/3] 构建Docker镜像..."
docker build -t $IMAGE_NAME .

# 停止并删除旧容器（如存在）
echo "[2/3] 停止并删除旧容器..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 启动新容器
echo "[3/3] 启动新容器..."
docker run -d \
  --name $CONTAINER_NAME \
  -p 5001:5001 \
  -p 5002:5002 \
  -v $(pwd)/conf:/app/conf \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -e TZ=Asia/Shanghai \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONIOENCODING=utf-8 \
  $IMAGE_NAME

echo "部署完成！访问 http://localhost:5002 查看UI，http://localhost:5001 查看API。"
