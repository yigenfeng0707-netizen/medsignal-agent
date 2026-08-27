#!/bin/bash
# ============================================================
# MedSignal 魔搭创空间入口
# - 后端 FastAPI   → 127.0.0.1:8000（内部）
# - 前端 Next.js   → 0.0.0.0:7860（对外，魔搭强制端口）
# - /api/* 由 Next rewrites 代理到本地 8000
# ============================================================
set -e

# 默认环境变量（优先保留平台注入的 variables/secrets，仅缺省时使用默认值）
export DEMO_OFFLINE="${DEMO_OFFLINE:-true}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////mnt/workspace/data/yibao.db}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-/mnt/workspace/chroma_data}"
export YIBAO_SESSION_SECRET="${YIBAO_SESSION_SECRET:-medsignal-modelscope-demo-secret-change-me}"

# 持久化目录（魔搭 /mnt/workspace 挂载点，重启不丢）
mkdir -p /mnt/workspace/data /mnt/workspace/chroma_data

echo "[entrypoint] 启动后端 uvicorn :8000 ..."
cd /app/backend
nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers 1 \
    > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端就绪（最多 90s）
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "[entrypoint] 后端就绪 ($i s)"
    break
  fi
  sleep 1
done

# 后端异常退出时终止容器
trap 'echo "[entrypoint] 后端进程已退出，关闭容器"; kill $BACKEND_PID 2>/dev/null || true' EXIT

echo "[entrypoint] 启动前端 node server.js :7860 ..."
cd /app/frontend
export PORT=7860
export HOSTNAME=0.0.0.0
exec node server.js
