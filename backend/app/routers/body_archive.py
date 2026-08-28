"""MedSignal - 档案管家 · 数字人体 3D 查看器适配路由

静态查看器 backend/app/static/digital-body/index.html（main.py 挂载于 /digital-body）
的数据契约，复用 routers/body.py 同一套 BodyRecord/BodyDocument 数据，只增不删：

- GET  /api/body-archive/patients                      患者索引（查看器左上角下拉切换）
- GET  /api/body-archive/patients/{user_id}            患者档案（性别 + 记录 + 资料）
- POST /api/body-archive/patients/{user_id}/records    追加一条档案（Skill ingest.py 用）
- POST /api/body-archive/patients/{user_id}/materials  登记资料文件名（不存文件本体）
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.services.body.extractor import DISCLAIMER
from app.services.body.taxonomy import LABELS

router = APIRouter(prefix="/api/body-archive", tags=["档案管家·数字人体"])

_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$")


def _user_ref(user_id: int) -> str:
    """查看器/前端通用的 'user_001' 形式患者 id。"""
    return f"user_{user_id:03d}"


def _norm_event_date(value: str) -> str:
    """校验并规范化 event_date：允许空串 / YYYY-MM / YYYY-MM-DD。"""
    value = (value or "").strip()
    if not value:
        return ""
    match = _DATE_RE.match(value)
    if not match or not 1 <= int(match.group(2)) <= 12:
        raise HTTPException(status_code=400, detail=f"event_date 格式不合法: {value!r}，应为 YYYY-MM 或 YYYY-MM-DD")
    out = f"{match.group(1)}-{int(match.group(2)):02d}"
    if match.group(3):
        if not 1 <= int(match.group(3)) <= 31:
            raise HTTPException(status_code=400, detail=f"event_date 日不合法: {value!r}")
        out += f"-{int(match.group(3)):02d}"
    return out


class BodyRecordIn(BaseModel):
    organ: str = Field(..., description="器官/部位 key，见 /api/body/organs")
    event_date: str = ""
    source_type: str = "chat"
    source_label: str = "对话输入"
    source_ref: str = ""
    description: str = ""
    raw_excerpt: str = ""


class MaterialIn(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    note: str = Field(default="", max_length=200)


@router.get("/patients")
async def list_patients(db: AsyncSession = Depends(get_db)):
    """患者索引：查看器下拉切换用。"""
    users = await crud.get_users(db, limit=50)
    return {"patients": [{"id": _user_ref(u.id), "name": u.name} for u in users]}


@router.get("/patients/{user_id}")
async def get_patient(user_id: str, db: AsyncSession = Depends(get_db)):
    """患者档案：性别（决定 3D 解剖模型）+ 档案记录 + 已存资料。"""
    user = await crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"患者不存在: {user_id}")
    records = [crud.body_record_to_dict(r) for r in await crud.get_body_records(db, user_id)]
    materials = [
        {"filename": d.filename, "note": d.doc_kind or ""}
        for d in await crud.get_body_documents(db, user_id)
    ]
    return {
        "patient_id": _user_ref(user.id),
        "name": user.name,
        "sex": "f" if user.gender in ("女", "female", "F") else "m",
        "records": records,
        "materials": materials,
        "disclaimer": DISCLAIMER,
    }


@router.post("/patients/{user_id}/records")
async def append_record(user_id: str, payload: BodyRecordIn, db: AsyncSession = Depends(get_db)):
    """追加一条档案记录（只增不删）。调用方（Skill/Agent）须保证内容来自用户原文。"""
    user = await crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"患者不存在: {user_id}")
    if payload.organ not in LABELS:
        raise HTTPException(status_code=400, detail=f"未知部位: {payload.organ}，可选 {list(LABELS)}")
    event_date = _norm_event_date(payload.event_date)
    rows = await crud.create_body_records(
        db,
        user_id,
        [{
            "organ": payload.organ,
            "description": payload.description or payload.raw_excerpt,
            "raw_excerpt": payload.raw_excerpt,
            "event_date": event_date,
        }],
        source_type=(payload.source_type or "chat")[:10],
        source_label=(payload.source_label or "对话输入")[:30],
        source_ref=payload.source_ref,
    )
    return {"record": crud.body_record_to_dict(rows[0])}


@router.post("/patients/{user_id}/materials")
async def register_material(user_id: str, payload: MaterialIn, db: AsyncSession = Depends(get_db)):
    """登记资料文件名与备注（只登记元数据，不接收文件本体）。"""
    user = await crud.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"患者不存在: {user_id}")
    doc = await crud.create_body_document(
        db, user_id, payload.filename, "", (payload.note or "其他")[:30], "",
    )
    return {"document": {"id": doc.id, "filename": doc.filename, "note": doc.doc_kind}}
