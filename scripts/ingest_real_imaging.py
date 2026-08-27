#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MedSignal - 真实公开医学影像数据集接入脚本

将公开数据集（胸片/肺CT/脑MRI）的影像转换为 MedSignal 影像引擎的
标准格式（512x512 灰度 PNG + 归一化 bbox），并在真实影像上运行
引擎自带的病灶检测流水线，产出可被后端 /api/imaging/real/* 端点
直接服务的 manifest.json 索引。

数据源（--source）：
  local       本地目录导入（PNG/JPG，DICOM 需 pydicom）——最可靠
  montgomery  NIH Montgomery County CXR（138 例胸片+肺野标注，直链）
  shenzhen    NIH Shenzhen ChinaSet（662 例胸片，直链）
  demo        内置合成图验证端到端管线（无需下载数据）

用法示例：
  python scripts/ingest_real_imaging.py --source demo
  python scripts/ingest_real_imaging.py --source local --dir path/to/pngs --study-type chest_xray --limit 20
  python scripts/ingest_real_imaging.py --source montgomery --limit 20
  python scripts/ingest_real_imaging.py --list

许可说明：
  - Montgomery/Shenzhen（NIH/LHNCBC）：公开可用，科研用途，请引用来源
  - 生产/商用请优先选择调研报告中的 CC BY 数据集（LIDC-IDRI / TCGA / ChestX-ray14）
  - 本脚本仅做小样本目录接入，不下载大规模档案

输出结构：
  data/real_imaging/
  ├── manifest.json   索引（source/study_type/image/detected/gt/metrics）
  ├── images/         512x512 标准化灰度 PNG
  └── raw/            原始下载
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import shutil
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ------------------------------------------------------------
# 路径与引擎加载（直连 engine.py，避免触发 services 包的 chromadb 依赖）
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
ENGINE_PATH = ROOT / "backend" / "app" / "services" / "imaging" / "engine.py"
OUT_DIR = ROOT / "data" / "real_imaging"
IMG_DIR = OUT_DIR / "images"
RAW_DIR = OUT_DIR / "raw"
MANIFEST_PATH = OUT_DIR / "manifest.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest")


def _load_engine():
    """按文件路径直连加载影像引擎（绕过 app.services 包级依赖）。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location("medsignal_imaging_engine", ENGINE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["medsignal_imaging_engine"] = mod
    spec.loader.exec_module(mod)
    return mod


engine = _load_engine()
IMG_SIZE = engine.IMG_SIZE          # 512
STUDY_TYPES = engine.STUDY_TYPES
FINDINGS_META = engine.FINDINGS_META
detect_findings = engine.detect_findings

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:  # pragma: no cover
    HAS_PIL = False
    log.error("Pillow 未安装，无法处理影像，请 pip install pillow")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:  # pragma: no cover
    HAS_REQUESTS = False

try:
    import pydicom
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False
    log.info("pydicom 未安装，DICOM 导入不可用（PNG/JPG 不受影响）")


# ------------------------------------------------------------
# NIH 直链数据集注册表
# ------------------------------------------------------------
NIH_DATASETS = {
    "montgomery": {
        "name": "NLM-Montgomery County CXR Set",
        "url": "https://openi.nlm.nih.gov/imgs/collections/NLM-MontgomeryCXRSet.zip",
        "org": "NIH / LHNCBC",
        "license": "公开科研用途（请引用 Jaeger et al. 2014）",
        "study_type": "chest_xray",
        "exts": (".png", ".jpg", ".jpeg"),
    },
    "shenzhen": {
        "name": "Shenzhen Hospital CXR Set (ChinaSet)",
        "url": "https://openi.nlm.nih.gov/imgs/collections/ChinaSet_AllFiles.zip",
        "org": "NIH / LHNCBC + 深圳第三人民医院",
        "license": "公开科研用途（请引用 Jaeger et al. 2014）",
        "study_type": "chest_xray",
        "exts": (".png", ".jpg", ".jpeg"),
    },
}

# 数据集病灶标签 -> FINDINGS_META key 映射（常见公开胸片标签）
LABEL_MAP = {
    "nodule": "nodule",
    "lung opacity": "infiltration",
    "infiltration": "infiltration",
    "infiltrate": "infiltration",
    "consolidation": "infiltration",
    "pneumonia": "infiltration",
    "effusion": "effusion",
    "pleural effusion": "effusion",
    "cardiomegaly": "cardiomegaly",
    "atelectasis": "infiltration",
    "pneumothorax": "pneumothorax",
    "emphysema": "emphysema",
    "fibrosis": "infiltration",
    "tuberculosis": "infiltration",
    "tb": "infiltration",
}


# ------------------------------------------------------------
# 影像读取与标准化
# ------------------------------------------------------------

def load_image_any(path: Path):
    """读取任意支持格式的影像为 0-255 灰度 ndarray；失败返回 None。"""
    if not HAS_PIL:
        return None
    suf = path.suffix.lower()
    try:
        if suf in (".dcm", ".dicom", ""):
            if not HAS_PYDICOM:
                log.warning("跳过 DICOM（未安装 pydicom）: %s", path.name)
                return None
            ds = pydicom.dcmread(str(path))
            arr = ds.pixel_array.astype(float)
            if arr.max() > 255:  # 窗位窗宽粗略归一化
                arr = (arr - arr.min()) / max(arr.max() - arr.min(), 1e-6) * 255
            return arr
        img = Image.open(path)
        if img.mode not in ("L", "I;16", "I"):
            img = img.convert("L")
        return np.asarray(img, dtype=float)
    except Exception as e:
        log.warning("读取失败 %s: %s", path.name, e)
        return None


def standardize(arr: np.ndarray, size: int = IMG_SIZE) -> np.ndarray:
    """灰度归一化 + 等比缩放到 size x size（居中留黑边，避免解剖比例失真）。"""
    h, w = arr.shape[:2]
    scale = size / max(h, w)
    nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
    pil = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(pil, ((size - nw) // 2, (size - nh) // 2))
    out = np.asarray(canvas, dtype=float)
    lo, hi = float(out.min()), float(out.max())
    if hi - lo < 1e-6:
        return out
    return (out - lo) / (hi - lo) * 255


def save_png(arr: np.ndarray, path: Path) -> str:
    """保存 0-255 灰度图为 PNG，返回 data URI base64。"""
    pil = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    pil.save(path, format="PNG")
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


# ------------------------------------------------------------
# GT 标注（可选）：从数据集附带标注文件解析归一化 bbox
# ------------------------------------------------------------

def parse_bbox_file(txt_path: Path, orig_shape) -> list:
    """解析 Montgomery 风格的矩形标注（首行 x1 y1 x2 y2，像素坐标）。"""
    h, w = orig_shape
    findings = []
    try:
        lines = txt_path.read_text().strip().splitlines()
        nums = [int(float(v)) for v in lines[0].split()] if lines else []
        if len(nums) != 4:
            return findings
        x1, y1, x2, y2 = nums
        cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
        bw, bh = abs(x2 - x1) / w, abs(y2 - y1) / h
        findings.append({
            "finding_type": "infiltration",
            "x": round(cx, 4), "y": round(cy, 4),
            "w": round(bw, 4), "h": round(bh, 4),
            "label": "数据集标注区域",
            "source": "dataset_gt", "confidence": 1.0,
        })
    except Exception as e:
        log.debug("解析标注失败 %s: %s", txt_path.name, e)
    return findings


def load_sidecar_labels(img_path: Path) -> list:
    """读取同名 .json 标注（用户自备 GT，简化格式 [{finding_type,x,y,w,h}, ...]，归一化）。"""
    p = img_path.with_suffix(".json")
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [d for d in data if "x" in d and "finding_type" in d]
    except Exception:
        pass
    return []


# ------------------------------------------------------------
# IoU 评估：引擎检测 vs 数据集 GT
# ------------------------------------------------------------

def iou_norm(a: dict, b: dict) -> float:
    ax1, ay1 = a["x"] - a["w"] / 2, a["y"] - a["h"] / 2
    ax2, ay2 = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
    bx1, by1 = b["x"] - b["w"] / 2, b["y"] - b["h"] / 2
    bx2, by2 = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / max(union, 1e-9)


def evaluate(detected: list, gt: list, iou_thr: float = 0.3) -> dict:
    """检测框与 GT 的 IoU 匹配（阈值 0.3，贪心单对匹配）。"""
    if not gt:
        return {"gt_count": 0, "det_count": len(detected), "matched": 0,
                "precision": None, "recall": None, "mean_iou": None}
    matched_pairs = []
    for i, d in enumerate(detected):
        for j, g in enumerate(gt):
            v = iou_norm(d, g)
            if v >= iou_thr:
                matched_pairs.append((v, i, j))
    matched_pairs.sort(reverse=True)
    used_d, used_g, matched, ious = set(), set(), 0, []
    for v, i, j in matched_pairs:
        if i in used_d or j in used_g:
            continue
        used_d.add(i); used_g.add(j); matched += 1; ious.append(v)
    precision = matched / len(detected) if detected else None
    recall = matched / len(gt) if gt else None
    return {
        "gt_count": len(gt), "det_count": len(detected), "matched": matched,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "mean_iou": round(sum(ious) / len(ious), 3) if ious else None,
        "iou_threshold": iou_thr,
    }


# ------------------------------------------------------------
# manifest 读写
# ------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            log.warning("manifest.json 损坏，将重建")
    return {"version": "1.0", "generated_at": "", "datasets": {}, "studies": []}


def save_manifest(m: dict) -> None:
    m["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# 核心导入流程：一张影像 -> 标准化 -> 检测 -> 评估 -> manifest 条目
# ------------------------------------------------------------

def ingest_one_image(img_path: Path, study_type: str, source_name: str,
                     index: int, gt_findings=None):
    arr = load_image_any(img_path)
    if arr is None:
        return None
    orig_shape = arr.shape[:2]
    std = standardize(arr)

    # 引擎检测（真实影像上的真实图像分析）
    findings = detect_findings(std, study_type)
    detected = [f.to_dict() for f in findings]

    # GT：显式传入优先，否则找 sidecar 标注
    if gt_findings is None:
        gt_findings = load_sidecar_labels(img_path)
    metrics = evaluate(detected, gt_findings or [])

    # 保存标准化影像
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    study_id = f"{source_name}_{index:04d}"
    img_out = IMG_DIR / f"{study_id}.png"
    image_data_uri = save_png(std, img_out)

    study = {
        "study_id": study_id,
        "study_type": study_type,
        "study_label": STUDY_TYPES[study_type]["label"],
        "source": source_name,
        "origin_file": img_path.name,
        "origin_shape": [int(orig_shape[0]), int(orig_shape[1])],
        "image_path": str(img_out.relative_to(ROOT)).replace("\\", "/"),
        "image_data_uri_len": len(image_data_uri),
        "detected_findings": detected,
        "gt_findings": gt_findings,
        "metrics": metrics,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    if metrics["mean_iou"] is not None:
        iou_msg = "IoU均值 " + str(metrics["mean_iou"])
    elif (gt_findings or []) and metrics["matched"] == 0:
        iou_msg = "无匹配(IoU<阈值)"
    else:
        iou_msg = "无GT标注"
    log.info(
        "[%s] %s 检出 %d 处 | GT %d | 命中 %d | %s",
        study_id, study_type, len(detected), len(gt_findings or []), metrics["matched"], iou_msg,
    )
    return study


# ------------------------------------------------------------
# 数据源：本地目录
# ------------------------------------------------------------

def source_local(dir_path: str, study_type: str, limit: int) -> list:
    d = Path(dir_path)
    if not d.is_dir():
        log.error("目录不存在: %s", d)
        return []
    if study_type not in STUDY_TYPES:
        log.error("不支持的检查类型 %s，可选 %s", study_type, list(STUDY_TYPES))
        return []
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".dcm")
    files = sorted(p for p in d.rglob("*") if p.suffix.lower() in exts)
    log.info("本地目录 %s：发现 %d 个影像文件", d, len(files))
    if limit > 0:
        files = files[:limit]
    studies = []
    for i, f in enumerate(files, 1):
        s = ingest_one_image(f, study_type, "local", i)
        if s:
            studies.append(s)
    return studies


# ------------------------------------------------------------
# 数据源：NIH 直链下载（montgomery / shenzhen）
# ------------------------------------------------------------

def download_file(url: str, dest: Path, timeout: int = 300) -> bool:
    if not HAS_REQUESTS:
        log.error("requests 未安装，无法下载；请 pip install requests 或改用 --source local")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log.info("已存在，跳过下载: %s", dest.name)
        return True
    try:
        log.info("下载 %s -> %s", url, dest)
        with requests.get(url, stream=True, timeout=timeout, verify=True) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            tmp.rename(dest)
        return True
    except Exception as e:
        log.error("下载失败: %s（可手动下载后用 --source local 导入）", e)
        return False


def extract_archive(archive: Path, out_dir: Path) -> bool:
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        if archive.suffix.lower() == ".zip":
            with zipfile.ZipFile(archive) as z:
                z.extractall(out_dir)
        elif archive.suffix.lower() in (".tar", ".gz", ".tgz"):
            with tarfile.open(archive) as t:
                t.extractall(out_dir)
        else:
            return False
        return True
    except Exception as e:
        log.error("解压失败: %s", e)
        return False


def source_nih(name: str, limit: int) -> list:
    meta = NIH_DATASETS[name]
    archive = RAW_DIR / f"{name}.zip"
    if not download_file(meta["url"], archive):
        return []
    extract_dir = RAW_DIR / name
    if not archive.exists() or not extract_archive(archive, extract_dir):
        return []

    exts = meta["exts"]
    files = sorted(p for p in extract_dir.rglob("*") if p.suffix.lower() in exts)
    log.info("%s 解压后影像 %d 个", meta["name"], len(files))
    if limit > 0:
        files = files[:limit]

    studies = []
    for i, f in enumerate(files, 1):
        gt = None
        # Montgomery：同名 .txt 为左/右肺野矩形标注（像素坐标）
        bbox_txt = f.with_suffix(".txt")
        if bbox_txt.exists():
            arr = load_image_any(f)
            if arr is not None:
                gt = parse_bbox_file(bbox_txt, arr.shape[:2])
        s = ingest_one_image(f, meta["study_type"], name, i, gt_findings=gt)
        if s:
            studies.append(s)
    return studies


# ------------------------------------------------------------
# 数据源：demo（内置合成图验证管线，无需下载）
# ------------------------------------------------------------

def source_demo() -> list:
    log.info("demo 模式：生成 3 张带病灶的合成影像验证端到端管线")
    tmp = Path(tempfile.mkdtemp(prefix="medsignal_ingest_demo_"))
    study_map = [("chest_xray", ["nodule", "infiltration"]),
                 ("lung_ct", ["nodule", "ground_glass"]),
                 ("brain_mri", ["tumor"])]
    studies = []
    for i, (st, keys) in enumerate(study_map, 1):
        rng = np.random.default_rng(2026 + i)
        findings = [engine.Finding(finding_type=k, x=0.4 + 0.12 * j, y=0.45, w=0.08, h=0.08)
                    for j, k in enumerate(keys)]
        if st == "chest_xray":
            arr = engine._render_chest_xray(rng, findings)
        elif st == "lung_ct":
            arr = engine._render_lung_ct(rng, findings)
        else:
            arr = engine._render_brain_mri(rng, findings)
        p = tmp / f"demo_{st}_{i}.png"
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(p)
        gt = [f.to_dict() for f in findings]
        s = ingest_one_image(p, st, "demo", i, gt_findings=gt)
        if s:
            studies.append(s)
    shutil.rmtree(tmp, ignore_errors=True)
    return studies


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def merge_into_manifest(source_name: str, studies: list) -> None:
    m = load_manifest()
    m.setdefault("datasets", {})
    m["datasets"].setdefault(source_name, {"count": 0})
    m["datasets"][source_name]["count"] += len(studies)
    m["datasets"][source_name]["updated_at"] = datetime.now(timezone.utc).isoformat()
    by_id = {s["study_id"]: s for s in m["studies"]}
    for s in studies:
        by_id[s["study_id"]] = s
    m["studies"] = sorted(by_id.values(), key=lambda s: s["study_id"])
    save_manifest(m)
    log.info("manifest 已更新：%d 条记录 -> %s", len(m["studies"]), MANIFEST_PATH)


def print_manifest_summary() -> None:
    m = load_manifest()
    total = len(m.get("studies", []))
    print("\n=== real_imaging manifest ===")
    print("文件: %s" % MANIFEST_PATH)
    print("研究总数: %d" % total)
    for ds, info in m.get("datasets", {}).items():
        print("  数据源 %s: %s 条" % (ds, info.get("count", 0)))
    by_type = {}
    for s in m.get("studies", []):
        by_type[s["study_type"]] = by_type.get(s["study_type"], 0) + 1
    for k, v in by_type.items():
        print("  类型 %s: %d 条" % (k, v))
    if m.get("studies"):
        print("\n最近 5 条：")
        for s in m["studies"][-5:]:
            mt = s.get("metrics") or {}
            print("  %s [%s] 检出 %d | GT %d | 命中 %s"
                  % (s["study_id"], s["study_type"],
                     len(s["detected_findings"]), len(s.get("gt_findings") or []),
                     mt.get("matched", "-")))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="MedSignal 真实公开影像数据集接入")
    parser.add_argument("--source", choices=["local", "montgomery", "shenzhen", "demo"],
                        default="demo", help="数据源")
    parser.add_argument("--dir", help="local 模式的影像目录")
    parser.add_argument("--study-type", default="chest_xray",
                        choices=list(STUDY_TYPES.keys()), help="检查类型（local 模式）")
    parser.add_argument("--limit", type=int, default=20, help="最多导入数量（0=不限）")
    parser.add_argument("--list", action="store_true", help="仅查看 manifest 概览")
    args = parser.parse_args()

    if args.list:
        print_manifest_summary()
        return 0

    studies = []
    if args.source == "local":
        if not args.dir:
            log.error("--source local 需要 --dir 指定影像目录")
            return 1
        studies = source_local(args.dir, args.study_type, args.limit)
    elif args.source in NIH_DATASETS:
        studies = source_nih(args.source, args.limit)
    elif args.source == "demo":
        studies = source_demo()

    if not studies:
        log.warning("没有导入任何影像")
        return 1

    merge_into_manifest(args.source, studies)
    print_manifest_summary()

    with_gt = [s for s in studies if s.get("gt_findings")]
    if with_gt:
        recalls = [s["metrics"]["recall"] for s in with_gt if s["metrics"]["recall"] is not None]
        if recalls:
            log.info("有 GT 样本平均召回率: %.3f（IoU>=0.3，规则引擎基线，非深度模型）",
                     sum(recalls) / len(recalls))
    log.info("完成：%d 条影像已入库。", len(studies))
    return 0


if __name__ == "__main__":
    sys.exit(main())
