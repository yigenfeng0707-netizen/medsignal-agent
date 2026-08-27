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

# 知识库索引播种：workspace 索引无数据时从镜像 seed 拷贝（幂等，重启不重复拷贝）
# ⚠️ 不能只看 chroma.sqlite3 是否存在：PersistentClient 初始化即建库文件，
# 曾放空库残留导致播种条件永远不满足（kb_chunks 恒为 0）。
# 改为用 sqlite 查 collections 表行数判定是否有有效数据。
if [ -d /app/chroma_seed ]; then
  need_seed=1
  if [ -f /mnt/workspace/chroma_data/chroma.sqlite3 ] && \
     python -c "import sqlite3,sys; con=sqlite3.connect('/mnt/workspace/chroma_data/chroma.sqlite3'); sys.exit(0 if con.execute('select count(*) from collections').fetchone()[0] > 0 else 1)" 2>/dev/null; then
    need_seed=0
    echo "[entrypoint] 知识库索引已存在，跳过播种"
  fi
  if [ "$need_seed" = "1" ]; then
    rm -rf /mnt/workspace/chroma_data/*
    cp -r /app/chroma_seed/. /mnt/workspace/chroma_data/
    echo "[entrypoint] 已播种知识库索引 seed -> /mnt/workspace/chroma_data"
  fi
fi

# 数据库初始化（幂等：users 表已有数据则跳过）
# - init_db.py 默认读取 /app/data/mock_data.json（Dockerfile 已 COPY data/ → /app/data/）
# - DATABASE_URL 指向 /mnt/workspace/data/yibao.db（持久化，重启不丢）
echo "[entrypoint] 初始化数据库（幂等）..."
cd /app/backend
python scripts/init_db.py 2>&1 | tee /tmp/init_db.log || {
  echo "[entrypoint] ⚠️ init_db.py 失败（不阻塞启动，后端 lifespan 会建空表）"
}

echo "[entrypoint] 启动后端 uvicorn :8000 ..."
cd /app/backend
nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers 1 \
    > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 实时输出后端日志到 stdout（魔搭日志能看到 LLM 调用错误、SQL 警告等）
tail -f /tmp/backend.log 2>/dev/null &
TAIL_PID=$!

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
