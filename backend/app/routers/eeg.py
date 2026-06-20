"""
医保智脑 - 脑电健康路由（EEG Router）

BCI×医保创新模块的 API 入口
- POST /api/eeg/{user_id}/session：发起一次 EEG 采集会话（合成信号 + 完整评估）
- GET  /api/eeg/{user_id}/latest：获取最近一次 EEG 评估
- GET  /api/eeg/{user_id}/history：EEG 历史趋势
- GET  /api/eeg/{user_id}/realtime：实时数据块（前端轮询模拟实时采集）
- GET  /api/eeg/{user_id}/policy-links：脑电异常 → 医保政策联动推荐
- GET  /api/eeg/states：支持的心理状态列表（前端场景选择用）
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.services.eeg import engine as eeg_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/eeg", tags=["脑电健康"])


@router.get("/states")
async def list_mental_states():
    """支持的心理状态列表（前端场景选择用）"""
    states = []
    for key, meta in eeg_engine.MENTAL_STATES.items():
        states.append({
            "key": key,
            "label": meta["label"],
            "stress": meta["stress"],
            "attention": meta["attention"],
            "sleep": meta["sleep"],
            "cognitive": meta["cognitive"],
        })
    return {"states": states, "channels": eeg_engine.CHANNELS, "sample_rate": eeg_engine.SAMPLE_RATE}


@router.post("/{user_id}/session")
async def create_eeg_session(
    user_id: str,
    mental_state: str = Query("auto", description="心理状态：auto/relaxed/focused/stressed/fatigued/sleep_deprived"),
    duration_seconds: int = Query(4, ge=1, le=30, description="采集时长（秒）"),
    db: AsyncSession = Depends(get_db),
):
    """发起一次 EEG 采集会话

    流程：合成信号 → 频域特征提取 → 健康指标 → 异常预警 → 医保政策联动 → 入库
    """
    profile = await crud.get_user_health_profile(db, user_id)
    if not profile.get("found"):
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    # auto 模式：根据用户画像推荐心理状态
    if mental_state == "auto":
        mental_state = eeg_engine.pick_mental_state_by_profile(profile)

    if mental_state not in eeg_engine.MENTAL_STATES:
        raise HTTPException(status_code=400, detail=f"不支持的心理状态：{mental_state}")

    # 完整评估
    session = eeg_engine.assess_session(
        user_id=user_id,
        mental_state=mental_state,
        duration_seconds=duration_seconds,
        user_profile=profile,
    )

    # 入库（摘要）
    try:
        await crud.create_eeg_record(
            db=db,
            user_id=user_id,
            session_id=session.session_id,
            duration_seconds=session.duration_seconds,
            mental_state=session.mental_state,
            mental_state_label=session.mental_state_label,
            avg_band_powers=session.avg_band_powers,
            metrics=session.metrics,
            alert_count=len(session.alerts),
            policy_link_count=len(session.policy_links),
            summary=session.summary,
        )
    except Exception as e:
        logger.warning("EEG 记录入库失败（不影响返回）: %s", e)

    return session.to_dict()


@router.get("/{user_id}/latest")
async def get_latest_eeg(user_id: str, db: AsyncSession = Depends(get_db)):
    """获取用户最近一次 EEG 评估（从数据库读取历史摘要，再实时生成波形）"""
    profile = await crud.get_user_health_profile(db, user_id)
    if not profile.get("found"):
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    record = await crud.get_latest_eeg_record(db, user_id)
    if record is None:
        # 无历史记录，实时生成一次
        mental_state = eeg_engine.pick_mental_state_by_profile(profile)
        session = eeg_engine.assess_session(
            user_id=user_id, mental_state=mental_state, user_profile=profile, seed=42,
        )
        return {**session.to_dict(), "from_history": False}

    # 历史摘要 + 实时波形（基于历史心理状态重新生成波形，保证可视化）
    signals, channels, sr = eeg_engine.generate_synthetic_eeg(
        mental_state=record.mental_state, seed=42,
    )
    waveform = eeg_engine._downsample_waveform(signals, channels, target_points=128)
    return {
        **crud.eeg_record_to_dict(record),
        "channels": channels,
        "sample_rate": sr,
        "waveform": waveform,
        "from_history": True,
    }


@router.get("/{user_id}/history")
async def get_eeg_history(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取用户 EEG 历史趋势"""
    profile = await crud.get_user_health_profile(db, user_id)
    if not profile.get("found"):
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    records = await crud.get_eeg_records(db, user_id, limit=limit)
    history = [crud.eeg_record_to_dict(r) for r in records]

    # 趋势聚合：压力/注意力/睡眠/认知负荷 4 维时序
    trend = []
    for r in reversed(records):  # 时间正序
        metrics = __import__("json").loads(r.metrics) if r.metrics else {}
        trend.append({
            "timestamp": r.recorded_at.isoformat() if r.recorded_at else None,
            "mental_state": r.mental_state,
            "mental_state_label": r.mental_state_label,
            "stress_index": metrics.get("stress_index", 0),
            "attention_index": metrics.get("attention_index", 0),
            "sleep_quality": metrics.get("sleep_quality", 0),
            "cognitive_load": metrics.get("cognitive_load", 0),
        })

    return {
        "user_id": user_id,
        "user_name": profile.get("name"),
        "total_sessions": len(history),
        "history": history,
        "trend": trend,
    }


@router.get("/{user_id}/realtime")
async def get_realtime_chunk(
    user_id: str,
    mental_state: str = Query("relaxed"),
    seed: int = Query(0, ge=0, le=100000),
):
    """实时数据块（前端轮询模拟实时采集，每次返回 1 秒数据）"""
    if mental_state not in eeg_engine.MENTAL_STATES:
        mental_state = "relaxed"
    return eeg_engine.realtime_stream(mental_state=mental_state, chunk_seconds=1.0, seed=seed or None)


@router.get("/{user_id}/policy-links")
async def get_policy_links(user_id: str, db: AsyncSession = Depends(get_db)):
    """脑电异常 → 医保政策联动推荐（基于最近一次 EEG 评估）"""
    profile = await crud.get_user_health_profile(db, user_id)
    if not profile.get("found"):
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

    record = await crud.get_latest_eeg_record(db, user_id)
    if record is None:
        # 无历史，实时评估一次
        mental_state = eeg_engine.pick_mental_state_by_profile(profile)
        session = eeg_engine.assess_session(
            user_id=user_id, mental_state=mental_state, user_profile=profile, seed=42,
        )
        return {
            "user_id": user_id,
            "user_name": profile.get("name"),
            "mental_state": session.mental_state,
            "mental_state_label": session.mental_state_label,
            "policy_links": session.policy_links,
            "summary": session.summary,
        }

    # 基于历史指标重新计算联动
    import json
    metrics = json.loads(record.metrics) if record.metrics else {}
    links = eeg_engine.link_to_policies(metrics, profile)
    return {
        "user_id": user_id,
        "user_name": profile.get("name"),
        "mental_state": record.mental_state,
        "mental_state_label": record.mental_state_label,
        "policy_links": links,
        "summary": record.summary or "",
    }
