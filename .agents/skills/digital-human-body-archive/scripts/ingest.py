#!/usr/bin/env python3
"""Append digital-body records or material metadata through the MedSignal API.

数据契约见 docs/api_contract.md 6.7 节与 SKILL.md：
- POST /api/body-archive/patients/<user_id>/records     追加一条档案记录
- POST /api/body-archive/patients/<user_id>/materials   登记资料文件名（不存文件本体）

器官 key 与日期校验复用后端 backend/app/services/body/taxonomy.py（直接按文件加载，
避免触发 app 包初始化）。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[3]
TAXONOMY_PATH = REPO_ROOT / "backend" / "app" / "services" / "body" / "taxonomy.py"
SPEC = importlib.util.spec_from_file_location("medsignal_body_taxonomy", TAXONOMY_PATH)
if not SPEC or not SPEC.loader:
    raise RuntimeError(f"无法加载器官分类模块：{TAXONOMY_PATH}")
TAXONOMY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TAXONOMY)
ORGAN_LABELS = TAXONOMY.LABELS
match_organs = TAXONOMY.match_organs

DATE_PATTERNS = (
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日?"),
    re.compile(r"(\d{4})年(\d{1,2})月"),
    re.compile(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?"),
)
DATE_FULL = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$")


def validate_event_date(value: str) -> str:
    """校验 YYYY-MM / YYYY-MM-DD；空串放行。不合法抛 ValueError。"""
    value = (value or "").strip()
    if not value:
        return ""
    match = DATE_FULL.match(value)
    if not match or not 1 <= int(match.group(2)) <= 12:
        raise ValueError(f"日期格式不合法: {value!r}，应为 YYYY-MM 或 YYYY-MM-DD")
    out = f"{match.group(1)}-{int(match.group(2)):02d}"
    if match.group(3):
        out += f"-{int(match.group(3)):02d}"
    return out


def extract_date(text: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        year, month = match.group(1), match.group(2)
        day = match.group(3) if match.lastindex == 3 else None
        candidate = f"{year}-{int(month):02d}" + (f"-{int(day):02d}" if day else "")
        try:
            return validate_event_date(candidate)
        except ValueError:
            return ""
    return ""


def infer_organ(sentence: str) -> str | None:
    organs = match_organs(sentence)
    return organs[0] if organs else None


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？；;\n]+", text) if len(part.strip()) >= 2]


def post_json(url: str, payload: dict, api_key: str = "") -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["X-API-Key"] = api_key
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API 返回 {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"无法连接 MedSignal API: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="MedSignal 数字人体档案追加接入")
    parser.add_argument("--patient", required=True, help="用户 id，如 user_001")
    parser.add_argument("--text", default="", help="病例原文")
    parser.add_argument("--organ", help="手动指定器官 key")
    parser.add_argument("--date", default="", help="YYYY-MM / YYYY-MM-DD")
    parser.add_argument("--source", default="对话输入", help="来源标签")
    parser.add_argument("--ref", default="", help="来源引用")
    parser.add_argument("--material", help="只登记资料文件名")
    parser.add_argument("--material-note", default="", help="资料备注")
    parser.add_argument(
        "--api",
        default=os.getenv("MEDSIGNAL_API_URL", "http://127.0.0.1:8000"),
        help="MedSignal API 基址",
    )
    parser.add_argument("--api-key", default=os.getenv("YIBAO_API_KEY", ""))
    args = parser.parse_args()

    api = args.api.rstrip("/")
    if args.material:
        result = post_json(
            f"{api}/api/body-archive/patients/{args.patient}/materials",
            {"filename": Path(args.material).name, "note": args.material_note},
            args.api_key,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.text.strip():
        parser.error("需要 --text，或使用 --material 登记资料")
    if args.organ and args.organ not in ORGAN_LABELS:
        parser.error(f"未知器官 key：{args.organ}")
    try:
        forced_date = validate_event_date(args.date)
    except ValueError as exc:
        parser.error(str(exc))

    added = []
    sentences = [args.text.strip()] if args.organ else split_sentences(args.text)
    for sentence in sentences:
        organ = args.organ or infer_organ(sentence)
        if not organ:
            continue
        payload = {
            "organ": organ,
            "event_date": forced_date or extract_date(sentence),
            "source_type": "chat" if args.source == "对话输入" else "upload",
            "source_label": args.source,
            "source_ref": args.ref,
            "description": sentence,
            "raw_excerpt": sentence,
        }
        added.append(
            post_json(
                f"{api}/api/body-archive/patients/{args.patient}/records",
                payload,
                args.api_key,
            )["record"]
        )

    if not added:
        parser.error("未识别到解剖部位；请用 --organ 指定 taxonomy key")
    print(json.dumps({"added": len(added), "records": added}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
