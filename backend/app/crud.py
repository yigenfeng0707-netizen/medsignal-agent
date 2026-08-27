"""
MedSignal - 统一数据访问层 (CRUD)

所有 Router / Service 通过本模块查询数据库，避免直接操作 session。
所有函数均为 async，接收 AsyncSession，返回 ORM 对象或标量。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DataAuthorization,
    EEGRecord,
    ImagingRecord,
    InsuranceRecord,
    MedicalRecord,
    MedicationRecord,
    PolicyDocument,
    User,
)

logger = logging.getLogger(__name__)


# ============================================================
# 用户
# ============================================================

async def get_user(db: AsyncSession, user_id: str | int) -> Optional[User]:
    """根据 user_id 查询用户。支持数字 id 或 'user_001' 形式。"""
    uid = _normalize_user_id(user_id)
    result = await db.execute(select(User).where(User.id == uid))
    return result.scalar_one_or_none()


async def get_users(db: AsyncSession, limit: int = 50) -> list[User]:
    """获取用户列表（多用户切换 Demo 用）。"""
    result = await db.execute(select(User).order_by(User.id).limit(limit))
    return list(result.scalars().all())


async def get_user_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(User.id)))
    return int(result.scalar() or 0)


# ============================================================
# 医保缴费记录
# ============================================================

async def get_insurance_records(
    db: AsyncSession, user_id: str | int, limit: int = 24
) -> list[InsuranceRecord]:
    """获取用户近 N 个月的缴费记录（按时间倒序）。"""
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(InsuranceRecord)
        .where(InsuranceRecord.user_id == uid)
        .order_by(desc(InsuranceRecord.year), desc(InsuranceRecord.month))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_payment_years(db: AsyncSession, user_id: str | int) -> int:
    """累计缴费月数 → 折算年数（向下取整）。"""
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(func.count(InsuranceRecord.id)).where(InsuranceRecord.user_id == uid)
    )
    months = int(result.scalar() or 0)
    return months


# ============================================================
# 就诊记录
# ============================================================

async def get_medical_records(
    db: AsyncSession, user_id: str | int, limit: int = 50
) -> list[MedicalRecord]:
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.user_id == uid)
        .order_by(desc(MedicalRecord.date))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_medical_records_in_range(
    db: AsyncSession, user_id: str | int, months: int = 6
) -> list[MedicalRecord]:
    """近 N 个月内的就诊记录（用于健康评分/政策匹配）。"""
    records = await get_medical_records(db=db, user_id=user_id, limit=200)
    # 过滤时间窗口（naive datetime 视为 UTC）
    import time
    cutoff = time.time() - months * 30 * 86400
    out = []
    for r in records:
        try:
            ts = r.date.replace(tzinfo=timezone.utc).timestamp() if r.date.tzinfo is None else r.date.timestamp()
        except Exception:
            ts = 0
        if ts >= cutoff:
            out.append(r)
    return out


# ============================================================
# 购药记录
# ============================================================

async def get_medication_records(
    db: AsyncSession, user_id: str | int, limit: int = 100
) -> list[MedicationRecord]:
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(MedicationRecord)
        .where(MedicationRecord.user_id == uid)
        .order_by(desc(MedicationRecord.date))
        .limit(limit)
    )
    return list(result.scalars().all())


# ============================================================
# 授权记录
# ============================================================

async def get_active_authorizations(
    db: AsyncSession, user_id: str | int
) -> list[DataAuthorization]:
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(DataAuthorization)
        .where(DataAuthorization.user_id == uid, DataAuthorization.is_active == True)  # noqa: E712
        .order_by(desc(DataAuthorization.authorized_at))
    )
    return list(result.scalars().all())


async def create_authorization(
    db: AsyncSession,
    user_id: str | int,
    data_type: str,
    authorized_agent: str,
    duration_days: int = 365,
) -> DataAuthorization:
    uid = _normalize_user_id(user_id)
    now = datetime.now(timezone.utc)
    expires_at = datetime.fromtimestamp(now.timestamp() + duration_days * 86400, tz=timezone.utc)
    auth = DataAuthorization(
        user_id=uid,
        data_type=data_type,
        authorized_agent=authorized_agent,
        authorized_at=now,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(auth)
    await db.commit()
    await db.refresh(auth)
    return auth


async def revoke_authorization(db: AsyncSession, auth_id: int) -> bool:
    result = await db.execute(
        select(DataAuthorization).where(DataAuthorization.id == auth_id)
    )
    auth = result.scalar_one_or_none()
    if auth is None:
        return False
    auth.is_active = False
    await db.commit()
    return True


# ============================================================
# 政策文档
# ============================================================

async def get_policy_documents(
    db: AsyncSession, category: Optional[str] = None, limit: int = 50
) -> list[PolicyDocument]:
    stmt = select(PolicyDocument).order_by(desc(PolicyDocument.publish_date)).limit(limit)
    if category:
        stmt = stmt.where(PolicyDocument.category == category)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_policy_document(db: AsyncSession, policy_id: int) -> Optional[PolicyDocument]:
    result = await db.execute(select(PolicyDocument).where(PolicyDocument.id == policy_id))
    return result.scalar_one_or_none()


# ============================================================
# 辅助：用户画像聚合（供 orchestrator / policy_matcher 使用）
# ============================================================

async def get_user_health_profile(db: AsyncSession, user_id: str | int) -> dict:
    """聚合用户健康画像原始数据（用药/就诊/慢病推断），供健康评分与 LLM 注入。

    返回结构化 dict，不含评分（评分由 health_engine 计算）。
    """
    uid = _normalize_user_id(user_id)
    user = await get_user(db, uid)
    if user is None:
        return {"user_id": uid, "found": False}

    meds = await get_medication_records(db, uid, limit=100)
    visits = await get_medical_records(db, uid, limit=100)

    # 慢病推断（基于购药分类）
    med_categories = {m.category for m in meds}
    chronic_diseases = []
    if any("降糖" in c or "糖尿病" in c for c in med_categories):
        chronic_diseases.append("糖尿病")
    if any("降压" in c or "高血压" in c for c in med_categories):
        chronic_diseases.append("高血压")
    if any("调脂" in c or "血脂" in c or "冠心" in c for c in med_categories):
        chronic_diseases.append("冠心病/高血脂")

    # 诊断推断（基于就诊记录）
    diagnoses = list({v.diagnosis for v in visits if v.diagnosis})[:10]

    return {
        "user_id": uid,
        "found": True,
        "name": user.name,
        "age": user.age,
        "gender": user.gender,
        "city": user.city,
        "insurance_type": user.insurance_type,
        "employee_status": user.employee_status,
        "chronic_diseases": chronic_diseases,
        "medication_categories": sorted(med_categories),
        "medications": [
            {
                "name": m.medication_name,
                "category": m.category,
                "date": m.date.isoformat() if m.date else None,
                "quantity": m.quantity,
                "unit_price": m.unit_price,
                "is_chronic": m.is_chronic,
            }
            for m in meds[:20]
        ],
        "recent_visits": len(visits),
        "visit_count_6m": len(await get_medical_records_in_range(db, uid, months=6)),
        "diagnoses": diagnoses,
        "annual_medical_cost": sum(v.total_cost or 0 for v in visits),
        "annual_medication_cost": sum((m.unit_price or 0) * (m.quantity or 0) for m in meds),
    }


# ============================================================
# 内部工具
# ============================================================

def _normalize_user_id(user_id: str | int) -> int:
    """把 'user_001' / '001' / 1 统一成 int。容错：解析失败返回 1。"""
    if isinstance(user_id, int):
        return user_id
    if user_id is None:
        return 1
    s = str(user_id).strip()
    # 提取数字部分
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return 1
    # 去掉前导零，但保证至少为 1
    n = int(digits.lstrip("0") or "0")
    return n if n > 0 else 1


# ============================================================
# EEG 脑电记录（BCI×医保创新模块）
# ============================================================

async def create_eeg_record(
    db: AsyncSession,
    user_id: str | int,
    session_id: str,
    duration_seconds: int,
    mental_state: str,
    mental_state_label: str,
    avg_band_powers: dict,
    metrics: dict,
    alert_count: int = 0,
    policy_link_count: int = 0,
    summary: str = "",
) -> EEGRecord:
    """保存一次 EEG 会话评估结果摘要。"""
    uid = _normalize_user_id(user_id)
    record = EEGRecord(
        user_id=uid,
        session_id=session_id,
        duration_seconds=duration_seconds,
        mental_state=mental_state,
        mental_state_label=mental_state_label,
        avg_band_powers=json.dumps(avg_band_powers, ensure_ascii=False),
        metrics=json.dumps(metrics, ensure_ascii=False),
        alert_count=alert_count,
        policy_link_count=policy_link_count,
        summary=summary,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_eeg_records(
    db: AsyncSession, user_id: str | int, limit: int = 20
) -> list[EEGRecord]:
    """获取用户 EEG 历史记录（按时间倒序）。"""
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(EEGRecord)
        .where(EEGRecord.user_id == uid)
        .order_by(desc(EEGRecord.recorded_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest_eeg_record(
    db: AsyncSession, user_id: str | int
) -> Optional[EEGRecord]:
    """获取用户最近一次 EEG 记录。"""
    records = await get_eeg_records(db, user_id, limit=1)
    return records[0] if records else None


def eeg_record_to_dict(record: EEGRecord) -> dict:
    """把 EEGRecord ORM 转为 dict（含反序列化的 JSON 字段）。"""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "session_id": record.session_id,
        "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
        "duration_seconds": record.duration_seconds,
        "mental_state": record.mental_state,
        "mental_state_label": record.mental_state_label,
        "avg_band_powers": json.loads(record.avg_band_powers) if record.avg_band_powers else {},
        "metrics": json.loads(record.metrics) if record.metrics else {},
        "alert_count": record.alert_count,
        "policy_link_count": record.policy_link_count,
        "summary": record.summary or "",
    }


# ============================================================
# 医学影像检查记录（MedSignal 影像引擎）
# ============================================================

async def create_imaging_record(
    db: AsyncSession,
    user_id: str | int,
    study_id: str,
    study_type: str,
    seed: int,
    findings: list | dict,
    final_findings: list | dict | None,
    report: dict | None,
    risk_level: str,
    policy_link_count: int = 0,
) -> ImagingRecord:
    """保存一次医学影像 AI 分析会话结果。"""
    uid = _normalize_user_id(user_id)
    record = ImagingRecord(
        user_id=uid,
        study_id=study_id,
        study_type=study_type,
        seed=seed,
        findings=json.dumps(findings, ensure_ascii=False),
        final_findings=json.dumps(final_findings, ensure_ascii=False) if final_findings is not None else None,
        report=json.dumps(report, ensure_ascii=False) if report is not None else None,
        risk_level=risk_level,
        policy_link_count=policy_link_count,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_imaging_records(
    db: AsyncSession, user_id: str | int, limit: int = 20
) -> list[ImagingRecord]:
    """获取用户医学影像检查历史（按时间倒序）。"""
    uid = _normalize_user_id(user_id)
    result = await db.execute(
        select(ImagingRecord)
        .where(ImagingRecord.user_id == uid)
        .order_by(desc(ImagingRecord.recorded_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_imaging_record(
    db: AsyncSession, record_id: int
) -> Optional[ImagingRecord]:
    """根据记录 id 查询医学影像检查记录。"""
    result = await db.execute(
        select(ImagingRecord).where(ImagingRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def update_imaging_record(
    db: AsyncSession,
    record: ImagingRecord,
    final_findings: list | dict | None = None,
    report: dict | None = None,
    risk_level: str | None = None,
    policy_link_count: int | None = None,
) -> ImagingRecord:
    """更新影像记录（医生复核后覆盖最终标注/报告）。"""
    if final_findings is not None:
        record.final_findings = json.dumps(final_findings, ensure_ascii=False)
    if report is not None:
        record.report = json.dumps(report, ensure_ascii=False)
    if risk_level is not None:
        record.risk_level = risk_level
    if policy_link_count is not None:
        record.policy_link_count = policy_link_count
    await db.commit()
    await db.refresh(record)
    return record


def imaging_record_to_dict(record: ImagingRecord) -> dict:
    """把 ImagingRecord ORM 转为 dict（含反序列化的 JSON 字段）。"""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "study_id": record.study_id,
        "study_type": record.study_type,
        "seed": record.seed,
        "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
        "findings": json.loads(record.findings) if record.findings else [],
        "final_findings": json.loads(record.final_findings) if record.final_findings else None,
        "report": json.loads(record.report) if record.report else None,
        "risk_level": record.risk_level,
        "policy_link_count": record.policy_link_count,
    }
