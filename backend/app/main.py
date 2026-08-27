import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import generate_session_token
from app.config import settings
from app.database import init_db
from app.routers import agents, body, claims, coverage, eeg, health_profile, imaging, policy, security
from app.services import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await orchestrator.initialize_services()
    yield


app = FastAPI(
    title="MedSignal Agent · 多模态医疗信号识别智能体",
    description="VentureD Hackathon HEALTHCARE 医疗赛道：脑电（EEG）健康分析 + 医学影像 AI 标注 + 可信数据空间，"
                "实现关键医疗信号识别与主动健康守护闭环",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS 配置：从环境变量读取，默认开放（Demo 模式）
# 生产环境通过 CORS_ORIGINS 收敛为白名单（逗号分隔）
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if _cors_origins_env.strip() == "*":
    _cors_origins = ["*"]
    _cors_credentials = False
else:
    _cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    _cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
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
app.include_router(imaging.router)
app.include_router(body.router)


@app.get("/api/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok", "service": "MedSignal Agent", "version": "3.0.0"}


@app.get("/api/health/detailed")
async def detailed_health_check():
    """详细健康检查：返回各依赖服务状态（P3-4 容错降级用）

    前端 ApiStatusIndicator 可据此展示 LLM/KB/DB 各项健康度。
    """
    deps = {}

    # LLM 状态
    deps["llm"] = {
        "available": orchestrator._llm is not None and orchestrator._llm.is_available,
        "primary_model": settings.LLM_MODEL,
        "fallback_model": settings.DASHSCOPE_MODEL,
    }

    # 视觉模型状态（影像解读用，未配置 Key 时自动关闭）
    try:
        from app.services.vision_service import get_vision_service
        _vs = get_vision_service()
        vision_ok = _vs is not None
    except Exception:
        vision_ok = False
    deps["vision"] = {
        "available": vision_ok,
        "model": settings.VISION_MODEL,
        "purpose": "医学影像自然语言解读（可选能力，降级不影响主流程）",
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

    # EEG 脑电引擎（脑电信号识别模块）
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

    # 医学影像 AI 标注引擎（影像信号识别模块）
    try:
        from app.services.imaging import STUDY_TYPES
        imaging_ok = True
    except Exception:
        imaging_ok = False
    deps["imaging_engine"] = {
        "available": imaging_ok,
        "study_types": list(STUDY_TYPES) if imaging_ok else [],
        "image_size": 512,
        "pipeline": "预处理 → 局部对比度增强 → 连通域分析 → 形态学特征分类",
    }

    all_ok = (
        all(d.get("available", False) for k, d in deps.items() if k != "vision")
        and deps["llm"].get("available", False)
    )
    return {
        "status": "ok" if all_ok else "degraded",
        "version": "3.0.0",
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
    from app import crud
    from app.database import async_session

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
