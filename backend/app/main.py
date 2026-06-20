from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import generate_session_token
from app.database import init_db
from app.routers import agents, claims, coverage, eeg, health_profile, policy, security
from app.services import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await orchestrator.initialize_services()
    yield


app = FastAPI(
    title="医保智脑",
    description="基于可信数据空间的个人医保智能体（BCI×医保创新版）",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(coverage.router)
app.include_router(claims.router)
app.include_router(health_profile.router)
app.include_router(policy.router)
app.include_router(security.router)
app.include_router(eeg.router)


@app.get("/api/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok", "service": "医保智脑", "version": "2.1.0"}


@app.get("/api/health/detailed")
async def detailed_health_check():
    """详细健康检查：返回各依赖服务状态（P3-4 容错降级用）

    前端 ApiStatusIndicator 可据此展示 LLM/KB/DB 各项健康度。
    """
    deps = {}

    # LLM 状态
    deps["llm"] = {
        "available": orchestrator._llm is not None and orchestrator._llm.is_available,
        "primary_model": "sensenova-6.7-flash-lite",
        "fallback_model": "qwen-plus",
    }

    # 知识库状态
    kb_ok = orchestrator._kb is not None
    kb_chunks = 0
    if kb_ok:
        try:
            stats = await orchestrator._kb.get_stats()
            kb_chunks = stats.get("total_chunks", 0)
        except Exception:
            pass
    deps["knowledge_base"] = {"available": kb_ok, "chunks": kb_chunks}

    # 数据库状态
    deps["database"] = {"available": True, "type": "sqlite"}

    # OCR
    deps["ocr"] = {"available": True, "provider": "ocr.space"}

    # EEG 脑电引擎（BCI×医保创新模块）
    try:
        import numpy as np  # noqa: F401
        eeg_ok = True
    except Exception:
        eeg_ok = False
    deps["eeg_engine"] = {
        "available": eeg_ok,
        "channels": 4,
        "sample_rate": 256,
        "bands": ["delta", "theta", "alpha", "beta", "gamma"],
    }

    all_ok = all(d.get("available", False) for d in deps.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "version": "2.1.0",
        "dependencies": deps,
        "demo_mode": orchestrator._llm is None,  # LLM 不可用时进入降级演示模式
    }


@app.post("/api/auth/login")
async def demo_login(phone: str = "13800000001"):
    """Demo 登录（手机号 + 验证码 mock），返回 token

    路演时演示：输入手机号 → 收到验证码（mock 1234）→ 登录成功
    """
    token = generate_session_token(phone)
    return {
        "token": token,
        "user_phone": phone,
        "expires_in": 86400,
        "message": "登录成功（Demo 模式，验证码固定为 1234）",
    }


@app.get("/api/users")
async def list_demo_users():
    """Demo 用户列表（用户切换器用，P3-2）

    返回数据库中的演示用户。前端 user-context 也有 mock 兜底。
    """
    from app.database import async_session
    from app import crud

    async with async_session() as db:
        users = await crud.get_users(db, limit=20)
        return {
            "users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "age": u.age,
                    "gender": u.gender,
                    "city": u.city,
                    "insurance_type": u.insurance_type,
                    "employee_status": u.employee_status,
                }
                for u in users
            ]
        }
