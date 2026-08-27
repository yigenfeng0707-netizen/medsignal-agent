"""Digital body archive API: append-only records grouped by anatomy."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.auth import require_api_key
from app.database import get_db
from app.schemas import BodyArchiveMaterialCreate, BodyArchiveRecordCreate
from app.services import body_archive

router = APIRouter(prefix="/api/body-archive", tags=["数字人体档案"])


def _http_user_id(value: str) -> int:
    try:
        return body_archive.normalize_user_id(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _require_user(db: AsyncSession, user_id: str):
    uid = _http_user_id(user_id)
    user = await crud.get_user(db, uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
    return user


async def _patient_payload(db: AsyncSession, user_id: str) -> dict:
    user = await _require_user(db, user_id)
    archive_records = await crud.get_body_archive_records(db, user.id, limit=500)
    medical_records = await crud.get_medical_records(db, user.id, limit=500)
    materials = await crud.get_body_archive_materials(db, user.id, limit=200)

    records = [body_archive.archive_record_to_dict(record) for record in archive_records]
    records.extend(
        item
        for record in medical_records
        if (item := body_archive.legacy_medical_record_to_dict(record)) is not None
    )
    records.sort(key=lambda item: (item.get("event_date", ""), item.get("created_at", "")))

    timestamps = [item["created_at"] for item in records if item.get("created_at")]
    timestamps.extend(
        body_archive.material_to_dict(material)["uploaded_at"]
        for material in materials
        if material.uploaded_at
    )
    return {
        "patient_id": body_archive.public_user_id(user.id),
        "name": user.name,
        "sex": "f" if user.gender in {"女", "female", "f"} else "m",
        "age": user.age,
        "updated_at": max(timestamps, default=""),
        "materials": [body_archive.material_to_dict(item) for item in materials],
        "records": records,
        "disclaimer": "仅整理展示已有资料，不构成临床诊断或治疗建议。",
    }


@router.get("/patients")
async def list_patients(db: AsyncSession = Depends(get_db)):
    users = await crud.get_users(db, limit=100)
    return {
        "patients": [
            {
                "id": body_archive.public_user_id(user.id),
                "name": f"{user.name} · {user.age}岁 · {user.gender}",
                "sex": "f" if user.gender in {"女", "female", "f"} else "m",
            }
            for user in users
        ]
    }


@router.get("/patients/{user_id}")
async def get_patient_archive(user_id: str, db: AsyncSession = Depends(get_db)):
    return await _patient_payload(db, user_id)


@router.get("/patients/{user_id}/records")
async def get_patient_records(
    user_id: str,
    organ: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    if organ is not None and organ not in body_archive.ORGAN_LABELS:
        raise HTTPException(status_code=400, detail="organ 不是合法的解剖部位 key")
    payload = await _patient_payload(db, user_id)
    records = payload["records"]
    if organ:
        records = [record for record in records if record.get("organ") == organ]
    return {"patient_id": payload["patient_id"], "total": len(records), "records": records}


@router.post(
    "/patients/{user_id}/records",
    status_code=status.HTTP_201_CREATED,
)
async def append_patient_record(
    user_id: str,
    payload: BodyArchiveRecordCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    user = await _require_user(db, user_id)
    if payload.organ not in body_archive.ORGAN_LABELS:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "organ 不是合法的解剖部位 key",
                "valid_organs": sorted(body_archive.ORGAN_LABELS),
            },
        )
    try:
        event_date = body_archive.validate_event_date(payload.event_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    description = payload.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="description 不能为空")

    record = await crud.create_body_archive_record(
        db,
        user.id,
        organ=payload.organ,
        event_date=event_date,
        source_type=payload.source_type.strip() or "upload",
        source_label=payload.source_label.strip() or "其他",
        source_ref=payload.source_ref.strip(),
        description=description,
        raw_excerpt=payload.raw_excerpt.strip() or description,
    )
    return {"ok": True, "record": body_archive.archive_record_to_dict(record)}


@router.post(
    "/patients/{user_id}/materials",
    status_code=status.HTTP_201_CREATED,
)
async def append_patient_material(
    user_id: str,
    payload: BodyArchiveMaterialCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_api_key),
):
    user = await _require_user(db, user_id)
    filename = re.split(r"[\\/]", payload.filename.strip())[-1]
    if not filename:
        raise HTTPException(status_code=400, detail="filename 必须包含文件名")
    material = await crud.create_body_archive_material(
        db, user.id, filename=filename, note=payload.note.strip()
    )
    return {"ok": True, "material": body_archive.material_to_dict(material)}
