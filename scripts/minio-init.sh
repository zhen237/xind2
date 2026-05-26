#!/bin/bash
# MinIO Bucket 初始化脚本
# 使用前确保 MinIO 已启动 (docker-compose up -d minio)

MC_ALIAS=local
MC_ENDPOINT=http://localhost:9000
MC_ACCESS_KEY=minioadmin
MC_SECRET_KEY=minioadmin

# 配置 mc 客户端
mc alias set $MC_ALIAS $MC_ENDPOINT $MC_ACCESS_KEY $MC_SECRET_KEY

# 创建各模块使用的 bucket
mc mb $MC_ALIAS/m03-models --ignore-existing
mc mb $MC_ALIAS/m04-media --ignore-existing
mc mb $MC_ALIAS/m05-telemetry --ignore-existing

# 设置公开读策略（前端需要直接访问模型文件）
mc policy set download $MC_ALIAS/m03-models

echo "MinIO buckets initialized:"
mc ls $MC_ALIAS
