"""
医保智脑 - 智能体编排路由

P0-1 升级：激活真实 AI 链路
- 移除 mock 优先 return 逻辑
- 真实走 orchestrator → LLM/RAG
- 从数据库注入用户画像作为 LLM 上下文
- mock 仅作为 orchestrator 内部最终降级兜底
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_api_key
from app.database import get_db
from app.schemas import ChatRequest
from app.services import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["智能体编排"])


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """智能体对话入口

    流程：意图识别(LLM优先) → 查库拿用户画像 → 路由到对应Agent → LLM/RAG生成 → 聚合
    """
    message = request.message
    user_id = request.user_id or "user_001"
    conversation_id = request.conversation_id

    # 1. 从数据库查询真实用户画像（用于个性化 LLM 上下文）
    user_profile = None
    try:
        user_profile = await crud.get_user_health_profile(db, user_id)
    except Exception as e:
        logger.warning("查询用户画像失败(user_id=%s): %s，将使用通用上下文", user_id, e)
        user_profile = None

    # 2. 意图识别（LLM 优先，关键词降级，30s 超时保护）
    try:
        import asyncio
        agent_type = await asyncio.wait_for(
            orchestrator.intent_recognition(message), timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.warning("意图识别超时(30s)，降级关键词匹配")
        agent_type = orchestrator._keyword_intent(message)
    logger.info("对话意图: %s | user_id=%s | message=%s", agent_type, user_id, message[:50])

    # 3. 路由到对应智能体（注入真实用户画像，40s 超时保护）
    try:
        result = await asyncio.wait_for(
            orchestrator.route_to_agent(agent_type, message, user_id, user_profile=user_profile),
            timeout=40.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Agent 路由超时(40s)，降级 mock")
        result = orchestrator.MOCK_RESPONSES.get(agent_type, {
            "response": "抱歉，AI 服务响应较慢，请稍后重试。",
            "data": {},
        })

    # 4. 聚合结果（补充通用建议）
    final = orchestrator.aggregate_results(result, agent_type=agent_type)

    return {
        "agent_type": final.get("agent_type", f"{agent_type}_agent"),
        "response": final["response"],
        "data": final.get("data", {}),
        "evidence": final.get("evidence"),
        "suggestions": final.get("suggestions", []),
        "user_profile": _brief_profile(user_profile),
        "conversation_id": conversation_id,
    }


def _brief_profile(profile: dict | None) -> dict | None:
    """返回精简的用户画像（前端展示用，不含敏感明细）。"""
    if not profile or not profile.get("found"):
        return None
    return {
        "name": profile.get("name"),
        "age": profile.get("age"),
        "insurance_type": profile.get("insurance_type"),
        "chronic_diseases": profile.get("chronic_diseases", []),
    }


@router.post("/complex-chat")
async def complex_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    """复合意图对话：多智能体并行协作（P2-1 核心亮点）

    示例："我父亲做心脏搭桥能报多少，有哪些政策能省钱"
    → 同时调度 权益管家 + 政策参谋 + 报销助手
    → LLM 融合各 Agent 回答，标注来源

    与 /chat 的区别：/chat 只识别单一主意图；/complex-chat 识别所有意图并行处理。
    """
    message = request.message
    user_id = request.user_id or "user_001"
    conversation_id = request.conversation_id

    user_profile = None
    try:
        user_profile = await crud.get_user_health_profile(db, user_id)
    except Exception as e:
        logger.warning("查询用户画像失败: %s", e)

    # 多意图并行调度 + 融合（orchestrator 内部已有 20s/20s 超时分段保护）
    # 外层再加 50s 总超时兜底，保证在 Render 60s 限制内返回
    import asyncio
    try:
        result = await asyncio.wait_for(
            orchestrator.handle_complex_query(message, user_id, user_profile=user_profile),
            timeout=50.0,
        )
    except asyncio.TimeoutError:
        logger.warning("complex-chat 总超时(50s)，返回超时提示")
        result = {
            "response": "您的问题涉及多个智能体协同，处理需要稍长时间。建议拆分为单个问题分别提问，或稍后重试。",
            "data": {"timeout": True},
            "agents_invoked": [],
            "multi_agent": True,
            "intent_weights": [],
        }

    agents_invoked = result.get("agents_invoked", [])
    multi_agent = result.get("multi_agent", False)
    intent_weights = result.get("intent_weights", [])

    return {
        "agent_type": "orchestrator_agent",
        "response": result.get("response", ""),
        "data": {
            **result.get("data", {}),
            "agents_invoked": agents_invoked,
            "multi_agent": multi_agent,
            "intent_weights": intent_weights,
        },
        "evidence": result.get("evidence"),
        "agents_invoked": agents_invoked,  # 顶层便于前端展示协作进度
        "multi_agent": multi_agent,
        "intent_weights": intent_weights,  # 顶层便于前端展示
        "suggestions": _complex_suggestions(agents_invoked),
        "user_profile": _brief_profile(user_profile),
        "conversation_id": conversation_id,
    }


def _complex_suggestions(agents: list[str]) -> list[str]:
    """根据触发的 Agent 组合给出综合建议"""
    suggestions = []
    if "coverage" in agents:
        suggestions.append("查看完整的医保权益和缴费记录")
    if "policy" in agents:
        suggestions.append("查看为您匹配的所有省钱政策")
    if "claims" in agents:
        suggestions.append("上传发票进行报销预审")
    if "health_profile" in agents:
        suggestions.append("查看您的健康画像和预警")
    if "eeg" in agents:
        suggestions.append("发起脑电采集，查看脑电健康指标")
    if not suggestions:
        suggestions.append("您可以问我医保报销、政策、健康、脑电等任何问题")
    return suggestions[:4]
