"""
MedSignal Agent - 医学影像 AI 标注路由

提供影像检查类型查询、AI 影像分析、医生复核标注、结构化报告、
影像-医保联动推荐等 API。前端影像标注工作台（/imaging）对接本模块。
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import async_session
from app.services.imaging import (
    FINDINGS_META,
    STUDY_TYPES,
    apply_doctor_review,
    build_report,
    generate_study,
    link_to_imaging_policies,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/imaging", tags=["imaging"])


# ============================================================
# Pydantic 请求模型
# ============================================================

class AnalyzeRequest(BaseModel):
    """发起一次影像 AI 分析。"""
    study_type: str = Field(..., description="检查类型：chest_xray / lung_ct / brain_mri")
    findings_keys: Optional[list[str]] = Field(
        default=None, description="植入病灶类别；缺省时使用该类型的全部类别"
    )
    seed: Optional[int] = Field(default=None, description="确定性种子，缺省时自动生成")


class DoctorAnnotation(BaseModel):
    """医生复核标注操作。"""
    action: str = Field(..., description="confirm / reject / add / update")
    index: Optional[int] = Field(default=None, description="AI 发现索引（confirm/reject 用）")
    finding_type: str = Field(default="nodule", description="病灶类别")
    x: float = Field(default=0.5, ge=0, le=1, description="归一化中心 x")
    y: float = Field(default=0.5, ge=0, le=1, description="归一化中心 y")
    w: float = Field(default=0.06, ge=0.01, le=1, description="归一化宽")
    h: float = Field(default=0.06, ge=0.01, le=1, description="归一化高")
    confidence: float = Field(default=0.9, ge=0, le=1, description="置信度")
    severity: str = Field(default="medium", description="严重度：low/medium/high")
    evidence: str = Field(default="医师人工复核标注", description="标注证据")


class DoctorReviewRequest(BaseModel):
    """医生复核请求：对 AI 预标注做确认/驳回/修正/新增。"""
    annotations: list[DoctorAnnotation] = Field(default_factory=list)


# ============================================================
# 接口
# ============================================================

@router.get("/study-types")
async def list_study_types():
    """支持的检查类型与病灶类别（前端标注工作台配置）。"""
    return {
        "study_types": {
            k: {
                "label": v["label"],
                "short_label": v["short_label"],
                "findings": [
                    {
                        "key": fk,
                        "label": FINDINGS_META[fk]["label"],
                        "severity": FINDINGS_META[fk]["severity"],
                        "desc": FINDINGS_META[fk]["desc"],
                    }
                    for fk in v["findings"]
                    if fk in FINDINGS_META
                ],
            }
            for k, v in STUDY_TYPES.items()
        }
    }


@router.post("/{user_id}/analyze")
async def analyze_image(user_id: str, req: AnalyzeRequest):
    """AI 影像分析：生成合成影像 → 病灶检测 → AI 预标注 → 结构化报告。

    现场路演演示：选择检查类型 → 一键生成影像 → AI 自动框出病灶并给出
    类别/置信度/严重度 → 医生可确认或修正。
    """
    if req.study_type not in STUDY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的检查类型: {req.study_type}，可选 {list(STUDY_TYPES)}",
        )

    study = generate_study(
        study_type=req.study_type,
        findings_keys=req.findings_keys,
        seed=req.seed,
    )

    # 医保联动
    policy_links = link_to_imaging_policies(study.findings)

    async with async_session() as db:
        from app import crud
        record = await crud.create_imaging_record(
            db=db,
            user_id=user_id,
            study_id=study.study_id,
            study_type=study.study_type,
            seed=study.seed,
            findings=[f.to_dict() for f in study.findings],
            final_findings=None,
            report=study.report,
            risk_level=study.report.get("risk_level", "待复核"),
            policy_link_count=len(policy_links),
        )

    return {
        "record_id": record.id,
        "study_id": study.study_id,
        "study_type": study.study_type,
        "study_label": STUDY_TYPES[study.study_type]["label"],
        "seed": study.seed,
        "image_base64": study.image_base64,
        "findings": [f.to_dict() for f in study.findings],
        "report": study.report,
        "policy_links": policy_links,
        "disclaimer": "本结果由 AI 辅助生成，仅供筛查参考，最终诊断须由持证医师复核确认。",
    }


@router.post("/{user_id}/records/{record_id}/review")
async def doctor_review(user_id: str, record_id: int, req: DoctorReviewRequest):
    """医生复核：确认/驳回/修正 AI 标注，生成最终报告。

    前端工作台演示：AI 预标注 → 医生逐框确认/驳回/修正 → 提交 →
    返回最终结构化报告与医保联动建议。
    """
    async with async_session() as db:
        from app import crud
        record = await crud.get_imaging_record(db, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="影像记录不存在")

        # 反序列化 AI 发现，构造 Finding 对象
        from app.services.imaging import Finding
        raw_findings = json.loads(record.findings) if record.findings else []
        ai_findings = [
            Finding(
                finding_type=f["finding_type"],
                x=f["x"], y=f["y"], w=f["w"], h=f["h"],
                confidence=f.get("confidence", 0.8),
                severity=f.get("severity", "medium"),
                source="ai",
                status=f.get("status", "pending"),
                evidence=f.get("evidence", ""),
            )
            for f in raw_findings
        ]

        # 应用医生标注
        ops = [a.dict() for a in req.annotations]
        final_findings = apply_doctor_review(ai_findings, ops)

        # 生成最终报告
        report = build_report(final_findings)
        policy_links = link_to_imaging_policies(final_findings)

        await crud.update_imaging_record(
            db=db,
            record=record,
            final_findings=[f.to_dict() for f in final_findings],
            report=report,
            risk_level=report.get("risk_level", "待复核"),
            policy_link_count=len(policy_links),
        )

    return {
        "record_id": record_id,
        "final_findings": [f.to_dict() for f in final_findings],
        "report": report,
        "policy_links": policy_links,
    }


@router.get("/{user_id}/records")
async def list_records(user_id: str, limit: int = Query(10, ge=1, le=50)):
    """用户医学影像检查历史。"""
    async with async_session() as db:
        from app import crud
        records = await crud.get_imaging_records(db, user_id, limit=limit)
        return {
            "records": [
                {
                    **crud.imaging_record_to_dict(r),
                    "study_label": STUDY_TYPES.get(r.study_type, {}).get("label", r.study_type),
                }
                for r in records
            ]
        }


@router.get("/{user_id}/records/{record_id}")
async def get_record(user_id: str, record_id: int):
    """单条影像记录详情（含可复现影像）。"""
    async with async_session() as db:
        from app import crud
        record = await crud.get_imaging_record(db, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="影像记录不存在")

        # 由确定性参数复现影像
        from app.services.imaging import Finding, render_study_image
        raw_findings = json.loads(record.findings) if record.findings else []
        findings = [
            Finding(
                finding_type=f["finding_type"],
                x=f["x"], y=f["y"], w=f["w"], h=f["h"],
                confidence=f.get("confidence", 0.8),
                severity=f.get("severity", "medium"),
                source=f.get("source", "ai"),
                status=f.get("status", "pending"),
                evidence=f.get("evidence", ""),
            )
            for f in raw_findings
        ]
        image_b64 = render_study_image(record.study_type, findings, record.seed)

        return {
            **crud.imaging_record_to_dict(record),
            "study_label": STUDY_TYPES.get(record.study_type, {}).get("label", record.study_type),
            "image_base64": image_b64,
        }


@router.get("/{user_id}/policy-links/{record_id}")
async def get_policy_links(user_id: str, record_id: int):
    """影像-医保联动推荐（基于最终标注）。"""
    async with async_session() as db:
        from app import crud
        record = await crud.get_imaging_record(db, record_id)
        if record is None:
            raise HTTPException(status_code=404, detail="影像记录不存在")
        raw_final = json.loads(record.final_findings) if record.final_findings else None
        raw_findings = json.loads(record.findings) if record.findings else []
        final_findings = raw_final if raw_final is not None else raw_findings

        from app.services.imaging import Finding
        f_list = [
            Finding(
                finding_type=f["finding_type"],
                x=f["x"], y=f["y"], w=f["w"], h=f["h"],
                confidence=f.get("confidence", 0.8),
                severity=f.get("severity", "medium"),
                source=f.get("source", "ai"),
                status=f.get("status", "pending"),
                evidence=f.get("evidence", ""),
            )
            for f in final_findings
        ]
        return {"policy_links": link_to_imaging_policies(f_list)}
