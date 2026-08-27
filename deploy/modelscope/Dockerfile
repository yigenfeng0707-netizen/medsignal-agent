# ============================================================
# MedSignal — 魔搭创空间全栈单容器镜像
# 架构：Next.js(standalone, 对外 7860) + FastAPI(内部 8000)
# 端口：对外固定 0.0.0.0:7860（魔搭平台强制）
# 说明：DEMO_OFFLINE=true 时后端全程离线降级（规则引擎），
#       无需 LLM API Key 即可演示全部核心链路。
# ============================================================

# ---------- Stage 1: 构建前端 (Next standalone) ----------
FROM node:18-bookworm-slim AS frontend-builder
WORKDIR /build/frontend
RUN corepack enable && corepack prepare pnpm@9 --activate

COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
# 同域部署：显式传空 → 前端 API_BASE 走相对路径 /api，无需知道公网域名
ENV NEXT_PUBLIC_API_URL=
ENV ENABLE_API_PROXY=1
RUN pnpm build

# ---------- Stage 2: 运行时 (Python + Node 双运行时) ----------
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 复制 Node 运行时（均为 Debian/glibc 系二进制，可互拷）
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-builder /usr/local/bin/npm /usr/local/bin/npm
COPY --from=frontend-builder /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 后端依赖（魔搭精简版：剔除 sentence-transformers/torch 等重型包）
COPY requirements-modelscope.txt ./
RUN pip install -r requirements-modelscope.txt

# 后端源码
COPY backend/ ./backend/
# 数据文件：所有引擎用 /app/data/*.json 规则库（claims/health/policy/eeg/imaging）
# init_db.py 默认从 /app/data/mock_data.json 读取种子数据
COPY data/ ./data/
# 持久化目录：/mnt/workspace 为魔搭创空间持久化挂载点（重启/迁移不丢数据）
RUN mkdir -p /app/backend/data /app/backend/chroma_data /mnt/workspace/data

# 前端 standalone 产物（本项目无 frontend/public，故不复制静态资源）
COPY --from=frontend-builder /build/frontend/.next/standalone ./frontend
COPY --from=frontend-builder /build/frontend/.next/static ./frontend/.next/static

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# 魔搭强制：对外 7860
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=90s \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["./entrypoint.sh"]
