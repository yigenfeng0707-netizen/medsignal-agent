"""
MedSignal - 最小鉴权层（P3-1）

设计原则：Demo 友好 + 安全叙事自洽
- 默认开放（无 token 也能访问，保证 Demo 流畅）
- 配置了 API_KEY 环境变量时，要求 X-API-Key 头校验
- 提供 get_current_user 依赖（基于 user_id 的简单会话）

这样"安全守门 Agent"名副其实，路演时可演示"未授权访问被拦截"。
"""

import hashlib
import logging
import os

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# 从环境变量读取 API Key（未配置则不启用鉴权，保证 Demo 流畅）
API_KEY = os.getenv("YIBAO_API_KEY", "")


def require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """API Key 校验依赖。

    - 未配置 YIBAO_API_KEY 环境变量时：跳过校验（Demo 模式）
    - 配置后：要求请求头 X-API-Key 匹配
    """
    if not API_KEY:
        return "anonymous"  # Demo 模式

    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key，请在请求头携带 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return "authenticated"


def get_current_user(
    user_id: str | None = None,
    x_user_token: str | None = Header(None, alias="X-User-Token"),
) -> dict:
    """获取当前用户（基于 token 的简易会话）。

    Demo 阶段：直接信任 user_id 参数（来自路径）
    生产阶段：解析 JWT token 提取 user_id
    """
    # Demo 模式：返回用户标识
    return {
        "user_id": user_id,
        "authenticated": bool(x_user_token),
        "demo_mode": True,
    }


def generate_session_token(user_id: str) -> str:
    """生成会话 token（简易版：user_id + 时间戳的哈希）"""
    import time
    raw = f"{user_id}|{time.time()}|{os.getenv('YIBAO_SESSION_SECRET', 'demo')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def verify_session_token(token: str) -> bool:
    """验证会话 token（Demo 阶段：非空即通过）"""
    return bool(token) and len(token) >= 16
