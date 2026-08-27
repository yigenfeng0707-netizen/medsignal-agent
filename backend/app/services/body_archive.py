"""Digital body archive taxonomy, validation, and serialization helpers."""

from __future__ import annotations

import re
from datetime import date

ORGAN_LABELS = {
    "brain": "脑部",
    "neck": "颈部",
    "lungs": "肺部",
    "heart": "心脏",
    "liver": "肝脏",
    "stomach": "胃部",
    "kidneys": "肾脏",
    "intestines": "肠道",
    "spleen": "脾脏",
    "pancreas": "胰腺",
    "spine": "脊柱",
    "chest": "胸部",
    "abdomen": "腹部",
    "pelvis": "盆腔",
    "uterus": "子宫",
    "ovaries": "卵巢",
    "prostate": "前列腺",
    "shoulder_l": "左肩",
    "shoulder_r": "右肩",
    "shoulder": "肩部",
    "arm_l": "左臂",
    "arm_r": "右臂",
    "arm": "手臂",
    "knee_l": "左膝",
    "knee_r": "右膝",
    "knee": "膝盖",
    "leg_l": "左腿",
    "leg_r": "右腿",
    "leg": "腿部",
}

ORGAN_ALIASES = {
    "brain": ("脑", "颅内", "头部"),
    "neck": ("甲状腺", "颈部", "鼻炎", "咽", "喉"),
    "lungs": ("肺", "支气管", "呼吸道"),
    "heart": ("心肌", "冠心", "冠状动脉", "心绞痛", "心脏", "高血压"),
    "liver": ("肝",),
    "stomach": ("胃",),
    "kidneys": ("肾", "尿路", "泌尿"),
    "intestines": ("结肠", "直肠", "阑尾", "肠"),
    "spleen": ("脾",),
    "pancreas": ("胰", "糖尿病"),
    "spine": ("脊柱", "腰椎", "颈椎", "椎间盘", "背部"),
    "chest": ("乳腺", "乳房", "胸部", "胸腔"),
    "abdomen": ("腹部", "腹痛"),
    "pelvis": ("骨盆", "盆腔", "髋"),
    "uterus": ("子宫", "宫腔"),
    "ovaries": ("卵巢", "输卵管"),
    "prostate": ("前列腺",),
    "shoulder_l": ("左肩",),
    "shoulder_r": ("右肩",),
    "shoulder": ("肩膀", "肩部", "肩"),
    "arm_l": ("左上肢", "左手臂", "左臂", "左肘", "左腕"),
    "arm_r": ("右上肢", "右手臂", "右臂", "右肘", "右腕"),
    "arm": ("上肢", "手臂", "胳膊", "肘", "腕"),
    "knee_l": ("左膝",),
    "knee_r": ("右膝",),
    "knee": ("膝关节", "膝盖", "膝"),
    "leg_l": ("左下肢", "左小腿", "左腿", "左踝"),
    "leg_r": ("右下肢", "右小腿", "右腿", "右踝"),
    "leg": ("下肢", "小腿", "腿部", "脚踝", "踝"),
}

_EVENT_DATE_RE = re.compile(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$")
_USER_ID_RE = re.compile(r"^(?:user_)?(\d{1,9})$")
_SIDE_FAMILIES = {
    "shoulder": {"shoulder_l", "shoulder_r"},
    "arm": {"arm_l", "arm_r"},
    "knee": {"knee_l", "knee_r"},
    "leg": {"leg_l", "leg_r"},
}


def normalize_user_id(value: str | int) -> int:
    """Accept positive numeric ids and the project's user_001 form."""
    match = _USER_ID_RE.fullmatch(str(value).strip())
    if not match or int(match.group(1)) <= 0:
        raise ValueError("用户 id 必须是正整数或 user_001 形式")
    return int(match.group(1))


def public_user_id(value: str | int) -> str:
    return f"user_{normalize_user_id(value):03d}"


def validate_event_date(value: str | None) -> str:
    """Validate YYYY-MM or YYYY-MM-DD while preserving partial dates."""
    if value in (None, ""):
        return ""
    match = _EVENT_DATE_RE.fullmatch(value)
    if not match:
        raise ValueError("事件日期必须是 YYYY-MM、YYYY-MM-DD 或留空")
    year, month, day = (int(part) if part else None for part in match.groups())
    if not 1900 < year < 2100 or not 1 <= month <= 12:
        raise ValueError("事件日期超出支持范围（1901-2099）")
    if day is not None:
        try:
            date(year, month, day)
        except ValueError as exc:
            raise ValueError("事件日期不是有效日历日期") from exc
    return value


def infer_organ(text: str) -> str | None:
    """Categorize supplied text by location without inferring a diagnosis."""
    hits = []
    for key, aliases in ORGAN_ALIASES.items():
        for alias in aliases:
            position = text.find(alias)
            if position >= 0:
                hits.append((position, -len(alias), key))
    if not hits:
        return None
    hits.sort()
    keys = {item[2] for item in hits}
    for _, _, key in hits:
        if key in _SIDE_FAMILIES and _SIDE_FAMILIES[key] & keys:
            continue
        return key
    return None


def archive_record_to_dict(record) -> dict:
    return {
        "id": f"body-{record.id}",
        "organ": record.organ,
        "event_date": record.event_date or "",
        "source_type": record.source_type,
        "source_label": record.source_label,
        "source_ref": record.source_ref,
        "description": record.description,
        "raw_excerpt": record.raw_excerpt,
        "created_at": _format_datetime(record.created_at),
    }


def legacy_medical_record_to_dict(record) -> dict | None:
    text = f"{record.diagnosis or ''} {record.department or ''}"
    organ = infer_organ(text)
    if not organ:
        return None
    event_date = record.date.strftime("%Y-%m-%d") if record.date else ""
    source_ref = " · ".join(part for part in (record.hospital, record.department) if part)
    return {
        "id": f"medical-{record.id}",
        "organ": organ,
        "event_date": event_date,
        "source_type": "medical_record",
        "source_label": f"{record.visit_type or '就诊'}记录",
        "source_ref": source_ref,
        "description": record.diagnosis or "就诊记录",
        "raw_excerpt": record.diagnosis or "",
        "created_at": event_date,
    }


def material_to_dict(material) -> dict:
    return {
        "filename": material.filename,
        "note": material.note,
        "uploaded_at": _format_datetime(material.uploaded_at),
    }


def _format_datetime(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else ""
