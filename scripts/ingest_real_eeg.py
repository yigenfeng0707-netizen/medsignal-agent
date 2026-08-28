#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MedSignal - 真实公开 EEG 数据集接入脚本

将公开 EEG 数据集（PhysioNet eegmmidb / OpenNeuro / 本地 EDF、CSV）的真实
脑电信号送入 MedSignal EEG 引擎（assess_real_session），产出五维健康指标
（压力/注意力/睡眠/认知负荷/情绪）、频段功率、预警与医保政策联动的
manifest.json 索引。

数据源（--source）：
  demo          内置合成信号验证端到端管线（无需下载，无 pyedflib 依赖）
  local         本地 EDF/EDF+/CSV 目录导入
  physionet     PhysioNet eegmmidb 单文件直链下载（无需账号）
  eegemotions27 EEGEmotions-27 情绪数据集（88 人×27 情绪，Emotiv X 256Hz）

用法示例：
  python scripts/ingest_real_eeg.py --source demo
  python scripts/ingest_real_eeg.py --source local --dir path/to/edf --limit 10
  python scripts/ingest_real_eeg.py --source physionet --subjects S001,S002 --runs 1,2
  python scripts/ingest_real_eeg.py --source eegemotions27
  python scripts/ingest_real_eeg.py --source eegemotions27 --pairs 10:5,10:17,10:20
  python scripts/ingest_real_eeg.py --list

EDF 解析：内置纯 Python 解析器（EDF/EDF+ 固定头 + 定长数据记录），
无 pyedflib 依赖；若已安装 pyedflib 则优先使用（更鲁棒）。

许可说明：
  - eegmmidb：ODC-By v1.0（需署名 Schalk et al. 2004 / PhysioNet）
  - eegemotions27：CC BY-NC 4.0（需署名 Phuong et al. 2025 IEEE Access，非商业）
  - OpenNeuro CC0 数据集：调研报告见 docs/EEG数据集调研.md
  - 本脚本仅下载/处理单文件级小样本，不做全量镜像

输出结构：
  data/real_eeg/
  ├── manifest.json   索引（五维指标/频段功率/预警/政策联动）
  └── raw/            原始 EDF 下载（gitignore，不入库）
"""

from __future__ import annotations

import argparse
import json
import logging
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ------------------------------------------------------------
# 路径与引擎加载（直连文件，避免触发 app.services 包级 chromadb 依赖）
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
EEG_PKG = ROOT / "backend" / "app" / "services" / "eeg"
OUT_DIR = ROOT / "data" / "real_eeg"
RAW_DIR = OUT_DIR / "raw"
MANIFEST_PATH = OUT_DIR / "manifest.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ingest_eeg")


def _load_module(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


engine = _load_module("ms_eeg_engine", EEG_PKG / "engine.py")
adapter = _load_module("ms_eeg_adapter", EEG_PKG / "device_adapter.py")

assess_real_session = engine.assess_real_session
generate_synthetic_eeg = engine.generate_synthetic_eeg
MENTAL_STATES = engine.MENTAL_STATES
from_numpy = adapter.from_numpy

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# eegmmidb 任务范式（1/2 基线，3/4 真实运动，7/8/11/12 运动想象）
PHYSIONET_RUNS = {
    1: ("relaxed", "基线·睁眼"),
    2: ("relaxed", "基线·闭眼"),
    3: ("focused", "任务·左拳(真实运动)"),
    4: ("focused", "任务·双拳(真实运动)"),
    7: ("focused", "任务·左拳(想象)"),
    8: ("focused", "任务·双拳(想象)"),
    11: ("focused", "任务·左拳(想象)"),
    12: ("focused", "任务·双拳(想象)"),
}


# ------------------------------------------------------------
# 内置纯 Python EDF/EDF+ 解析器（零依赖 fallback）
# ------------------------------------------------------------

def parse_edf_pure(path: Path):
    """解析 EDF/EDF+ 文件，返回 (signals, channels, sample_rate)。

    支持两种信号头布局：
    - 行式（标准 EDF）：每通道 256 字节连续
    - 列式（BCI2000 导出，如 PhysioNet eegmmidb）：同名字段连续排列
      labels(16×ns) transducer(80×ns) phys_dim(8×ns) phys_min/max(8×ns)
      dig_min/max(8×ns) prefiltering(80×ns) spr(8×ns) reserved(32×ns)

    signals: list[np.ndarray]（物理单位，通常 μV）
    channels: list[str]（跳过 EDF+ Annotations 信号）
    """
    data = path.read_bytes()
    if len(data) < 256:
        raise ValueError("文件过短，不是有效 EDF")

    header = data[:256]
    ns = int(header[252:256].decode("ascii", "ignore").strip() or "0")
    record_count = int(header[236:244].decode("ascii", "ignore").strip() or "0")
    record_duration = float(header[244:252].decode("ascii", "ignore").strip() or "0")
    if ns <= 0 or record_duration <= 0 or record_count <= 0:
        raise ValueError("EDF 头解析失败（ns/record_count/record_duration 非法）")

    def _f(b: bytes, default: float) -> float:
        s = b.decode("ascii", "ignore").strip()
        try:
            return float(s)
        except ValueError:
            return default

    # 尝试行式布局：每通道 256 字节，spr 在 216-224
    row_ok = True
    sprs_row = []
    for i in range(ns):
        c = data[256 + i * 256: 256 + (i + 1) * 256]
        spr = _f(c[216:224], 0)
        if spr <= 0:
            row_ok = False
            break
        sprs_row.append(int(spr))
    if row_ok:
        block_bytes = sum(sprs_row) * 2
        data_start = 256 + ns * 256
        if data_start + record_count * block_bytes > len(data) + block_bytes:
            row_ok = False  # 数据区越界，行式不成立

    if row_ok:
        labels, phys_mins, phys_maxs, dig_mins, dig_maxs, sprs = [], [], [], [], [], []
        for i in range(ns):
            c = data[256 + i * 256: 256 + (i + 1) * 256]
            labels.append(c[0:16].decode("ascii", "ignore").strip())
            dmin = _f(c[120:128], -32768)
            dmax = _f(c[128:136], 32767)
            phys_mins.append(_f(c[104:112], dmin))
            phys_maxs.append(_f(c[112:120], dmax))
            dig_mins.append(dmin)
            dig_maxs.append(dmax)
            sprs.append(int(_f(c[216:224], 0)))
        data_start = 256 + ns * 256
    else:
        # 列式布局（BCI2000/eegmmidb）：字段按列连续排列
        base = 256
        label_off = base
        trans_off = label_off + ns * 16
        pdim_off = trans_off + ns * 80
        pmin_off = pdim_off + ns * 8
        pmax_off = pmin_off + ns * 8
        dmin_off = pmax_off + ns * 8
        dmax_off = dmin_off + ns * 8
        pre_off = dmax_off + ns * 8
        spr_off = pre_off + ns * 80
        data_start = spr_off + ns * 8 + ns * 32
        labels, phys_mins, phys_maxs, dig_mins, dig_maxs, sprs = [], [], [], [], [], []
        for i in range(ns):
            labels.append(data[label_off + i * 16: label_off + i * 16 + 16].decode("ascii", "ignore").strip())
            phys_mins.append(_f(data[pmin_off + i * 8: pmin_off + i * 8 + 8], 0))
            phys_maxs.append(_f(data[pmax_off + i * 8: pmax_off + i * 8 + 8], 1))
            dig_mins.append(_f(data[dmin_off + i * 8: dmin_off + i * 8 + 8], -32768))
            dig_maxs.append(_f(data[dmax_off + i * 8: dmax_off + i * 8 + 8], 32767))
            sprs.append(int(_f(data[spr_off + i * 8: spr_off + i * 8 + 8], 0)))
        if any(s <= 0 for s in sprs):
            raise ValueError("列式信号头 spr 解析失败（非 BCI2000 布局？）")
        log.info("检测到列式信号头（BCI2000 导出格式），ns=%d spr=%d", ns, sprs[0])

    # 每个数据记录的总字节数（所有通道的采样数之和 × 2 字节 int16）
    block_bytes = sum(sprs) * 2
    if block_bytes <= 0 or data_start + block_bytes > len(data):
        raise ValueError("EDF 数据区不完整")

    signals, channels = [], []
    sample_rate = 0
    for i in range(ns):
        lb = labels[i]
        if lb.lower().startswith("edf annotations"):
            continue
        spr = sprs[i]
        if spr <= 0:
            continue
        sample_rate = int(round(spr / record_duration))
        # 该通道在每条数据记录内的字节偏移：位于其前（含 annotation）的全部通道采样数
        intra_offset = sum(sprs[:i]) * 2
        vals = []
        offset = data_start
        for _ in range(record_count):
            if offset + intra_offset + spr * 2 > len(data):
                break
            vals.extend(struct.unpack_from("<%dh" % spr, data, offset + intra_offset))
            offset += block_bytes
        dig = np.asarray(vals, dtype=float)
        pmin, pmax = phys_mins[i], phys_maxs[i]
        dmin, dmax = dig_mins[i], dig_maxs[i]
        if dmax - dmin != 0:
            phys = (dig - dmin) / (dmax - dmin) * (pmax - pmin) + pmin
        else:
            phys = dig
        signals.append(phys)
        channels.append(lb)

    if not signals or sample_rate <= 0:
        raise ValueError("未解析到有效 EEG 通道")
    return signals, channels, sample_rate


def load_eeg_file(path: Path):
    """读取 EEG 文件（EDF 优先 pyedflib，fallback 纯 Python；CSV 走 device_adapter）。"""
    suf = path.suffix.lower()
    if suf in (".edf", ".edf+", ".bdf"):
        try:
            import pyedflib  # 若已安装则优先
            f = pyedflib.EdfReader(str(path))
            sigs, chans = [], []
            for i in range(f.signals_in_file):
                lb = f.getLabel(i)
                if lb.lower().startswith("edf annotations"):
                    continue
                sigs.append(f.readSignal(i).astype(float))
                chans.append(lb)
            sr = int(f.getSampleFrequency(0))
            f.close()
            if sigs:
                return sigs, chans, sr
        except ImportError:
            pass
        return parse_edf_pure(path)
    if suf in (".csv", ".txt"):
        sigs, chans, sr, info = adapter.load_from_csv(
            path.read_bytes(), sample_rate=0, filename=path.name,
        )
        return sigs, chans, sr
    raise ValueError(f"不支持的文件格式: {suf}（支持 .edf/.csv/.txt）")


# ------------------------------------------------------------
# manifest 读写
# ------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            log.warning("manifest.json 损坏，将重建")
    return {"version": "1.0", "generated_at": "", "datasets": {}, "sessions": []}


def save_manifest(m: dict) -> None:
    m["generated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# 核心导入流程：一份真实 EEG -> 通道映射 -> 引擎评估 -> manifest 条目
# ------------------------------------------------------------

def ingest_one_recording(signals, channels, sr, source_name, record_id,
                         mental_state="auto", user_profile=None, meta=None):
    # 通道映射到 Muse 布局（>4 通道时择优取 4 通道，防 extract_band_powers 通道错位）
    sig_mapped, ch_mapped, sr_mapped, info = from_numpy(
        signals=list(signals), channels=list(channels), sample_rate=sr,
    )
    device_info = info.to_dict() if hasattr(info, "to_dict") else {
        "source": source_name, "sample_rate": sr_mapped,
    }
    device_info["source"] = "dataset"
    device_info["dataset"] = source_name

    session = assess_real_session(
        user_id="dataset",
        signals=sig_mapped,
        channels=ch_mapped,
        sample_rate=sr_mapped,
        mental_state=mental_state,
        user_profile=user_profile,
        device_info=device_info,
    )
    entry = session.to_dict()
    entry["record_id"] = record_id
    entry["source"] = source_name
    entry["origin_channels"] = list(channels)
    entry["origin_sample_rate"] = sr
    if meta:
        entry["dataset_meta"] = meta

    log.info("[%s] 状态=%s 预警=%d条 指标=%s",
             record_id, entry.get("mental_state"), len(entry.get("alerts") or []),
             {k: (v.get("value") if isinstance(v, dict) else v)
              for k, v in (entry.get("metrics") or {}).items()})
    return entry


# ------------------------------------------------------------
# 数据源：本地目录
# ------------------------------------------------------------

def source_local(dir_path: str, limit: int) -> list:
    d = Path(dir_path)
    if not d.is_dir():
        log.error("目录不存在: %s", d)
        return []
    files = sorted(p for p in d.rglob("*") if p.suffix.lower() in (".edf", ".csv", ".txt"))
    log.info("本地目录 %s：发现 %d 个 EEG 文件", d, len(files))
    if limit > 0:
        files = files[:limit]
    entries = []
    for i, f in enumerate(files, 1):
        try:
            sigs, chans, sr = load_eeg_file(f)
            e = ingest_one_recording(sigs, chans, sr, "local", f"local_{i:04d}")
            e["origin_file"] = f.name
            entries.append(e)
        except Exception as ex:
            log.warning("导入失败 %s: %s", f.name, ex)
    return entries


# ------------------------------------------------------------
# 数据源：PhysioNet eegmmidb 直链
# ------------------------------------------------------------

def download(url: str, dest: Path, timeout: int = 120) -> bool:
    if not HAS_REQUESTS:
        log.error("requests 未安装，无法下载；请 pip install requests 或改用 --source local")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        log.info("下载 %s", url)
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            tmp.rename(dest)
        return True
    except Exception as e:
        log.error("下载失败 %s: %s", url, e)
        return False


def source_physionet(subjects: list, runs: list) -> list:
    entries = []
    for subj in subjects:
        subj = subj.strip().upper()
        if not subj.startswith("S"):
            subj = "S" + subj.zfill(3)
        for run in runs:
            run = int(run)
            if run not in PHYSIONET_RUNS:
                log.warning("跳过 run %d（非标准任务 run）", run)
                continue
            state_key, state_label = PHYSIONET_RUNS[run]
            url = f"https://physionet.org/files/eegmmidb/1.0.0/{subj}/{subj}R{run:02d}.edf"
            dest = RAW_DIR / "eegmmidb" / f"{subj}R{run:02d}.edf"
            if not download(url, dest):
                continue
            try:
                sigs, chans, sr = load_eeg_file(dest)
                e = ingest_one_recording(
                    sigs, chans, sr, "eegmmidb",
                    f"{subj}R{run:02d}",
                    mental_state=state_key if state_key in MENTAL_STATES else "auto",
                    meta={"subject": subj, "run": run, "paradigm": state_label,
                          "license": "ODC-By v1.0 (PhysioNet, Schalk et al. 2004)"},
                )
                e["origin_file"] = dest.name
                entries.append(e)
            except Exception as ex:
                log.warning("导入失败 %s: %s", dest.name, ex)
    return entries


# ------------------------------------------------------------
# 数据源：EEGEmotions-27（情绪诱发，GitHub huytungst/EEGEmotions-27）
# ------------------------------------------------------------

# 27 种细粒度情绪标签（数据集官方 Emotion ID 映射）
EEGEMOTIONS27_EMOTIONS = {
    1: "admiration", 2: "adoration", 3: "aesthetic", 4: "amusement",
    5: "anger", 6: "anxiety", 7: "awes", 8: "awkwardness",
    9: "boredom", 10: "calmness", 11: "confusion", 12: "craving",
    13: "disgust", 14: "empathic pain", 15: "entrancement", 16: "excitement",
    17: "fear", 18: "horror", 19: "interest", 20: "joy",
    21: "nostalgia", 22: "relief", 23: "romance", 24: "sadness",
    25: "satisfaction", 26: "sexual desire", 27: "surprised",
}

# Emotiv X 头环 14 通道顺序（emotivX_channels_location.ced）
EMOTIV_X_CHANNELS = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
                      "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]

EEGEMOTIONS27_SAMPLE_RATE = 256
# Emotiv 14-bit ADC 标定：0.51 μV/LSB（接入前去直流偏移再标定）
EMOTIV_UV_PER_LSB = 0.51

# 默认样本：受试者 10 的 5 个代表性情绪（anger/fear/joy/calmness/sadness）
EEGEMOTIONS27_DEFAULT_PAIRS = [(10, 5), (10, 17), (10, 20), (10, 10), (10, 24)]


def _parse_eegemotions27(path: Path):
    """解析 EEGEmotions-27 文本文件（tab 分隔 14 列，无表头）。

    返回 (signals, channels, sample_rate)：逐通道去均值后按 0.51 μV/LSB
    标定为 μV 量级（指标基于频段比值，标定仅影响幅度类质量判定）。
    """
    arr = np.loadtxt(path, delimiter="\t", ndmin=2)
    if arr.ndim != 2 or arr.shape[1] != len(EMOTIV_X_CHANNELS):
        raise ValueError(f"列数异常: {arr.shape}（预期 14 通道）")
    signals = [(arr[:, i] - arr[:, i].mean()) * EMOTIV_UV_PER_LSB
               for i in range(arr.shape[1])]
    return signals, list(EMOTIV_X_CHANNELS), EEGEMOTIONS27_SAMPLE_RATE


def source_eegemotions27(pairs: list) -> list:
    """下载并接入 EEGEmotions-27 情绪样本。

    pairs: [(participant, emotion_id), ...]；公开数据集仅含自评 4-5 分的
    有效诱发 trial，若指定文件不存在则跳过并告警。
    """
    entries = []
    for participant, emotion_id in pairs:
        emotion = EEGEMOTIONS27_EMOTIONS.get(int(emotion_id), f"emotion{emotion_id}")
        url = ("https://raw.githubusercontent.com/huytungst/EEGEmotions-27/main/"
               f"eeg_raw/{participant}_{emotion_id}.0.txt")
        dest = RAW_DIR / "eegemotions27" / f"p{int(participant):02d}_e{int(emotion_id):02d}.txt"
        if not download(url, dest):
            log.warning("跳过 %s（该受试者-情绪组合不在公开数据集中）", dest.name)
            continue
        try:
            sigs, chans, sr = _parse_eegemotions27(dest)
            record_id = f"emo27_p{int(participant):02d}_e{int(emotion_id):02d}"
            e = ingest_one_recording(
                sigs, chans, sr, "eegemotions27", record_id,
                mental_state="auto",  # 由引擎按频段比值自动推断，不作先验假设
                meta={
                    "participant": int(participant),
                    "emotion_id": int(emotion_id),
                    "emotion": emotion,
                    "paradigm": f"情绪诱发（视频片段）· {emotion}",
                    "device": "Emotiv X 头环（14 通道，256Hz）",
                    "channels_layout": "Emotiv EPOC（AF3/F7/.../AF4）",
                    "unit_conversion": f"去均值 × {EMOTIV_UV_PER_LSB} μV/LSB",
                    "license": "CC BY-NC 4.0 (huytungst/EEGEmotions-27)",
                    "citation": "Phuong et al. 2025, IEEE Access, DOI:10.1109/ACCESS.2025.3620677",
                },
            )
            e["origin_file"] = dest.name
            entries.append(e)
        except Exception as ex:
            log.warning("导入失败 %s: %s", dest.name, ex)
    return entries


# ------------------------------------------------------------
# 数据源：demo（合成信号验证管线，无需下载）
# ------------------------------------------------------------

def source_demo() -> list:
    log.info("demo 模式：3 种心理状态的合成信号验证端到端管线")
    entries = []
    for i, state in enumerate(["stressed", "focused", "relaxed"], 1):
        signals, channels, sr = generate_synthetic_eeg(mental_state=state)
        e = ingest_one_recording(
            signals, channels, sr, "demo", f"demo_{i:04d}",
            mental_state=state,
            meta={"synthetic": True, "expected_state": state},
        )
        entries.append(e)
    return entries


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def merge_into_manifest(source_name: str, entries: list) -> None:
    m = load_manifest()
    m.setdefault("datasets", {})
    m["datasets"].setdefault(source_name, {"count": 0})
    m["datasets"][source_name]["count"] += len(entries)
    m["datasets"][source_name]["updated_at"] = datetime.now(timezone.utc).isoformat()
    by_id = {s["record_id"]: s for s in m["sessions"]}
    for e in entries:
        by_id[e["record_id"]] = e
    m["sessions"] = sorted(by_id.values(), key=lambda s: s["record_id"])
    save_manifest(m)
    log.info("manifest 已更新：%d 条记录 -> %s", len(m["sessions"]), MANIFEST_PATH)


def print_summary() -> None:
    m = load_manifest()
    print("\n=== real_eeg manifest ===")
    print("文件: %s" % MANIFEST_PATH)
    print("评估总数: %d" % len(m.get("sessions", [])))
    for ds, info in m.get("datasets", {}).items():
        print("  数据源 %s: %s 条" % (ds, info.get("count", 0)))
    states = {}
    for s in m.get("sessions", []):
        states[s.get("mental_state")] = states.get(s.get("mental_state"), 0) + 1
    print("  心理状态分布: %s" % states)
    if m.get("sessions"):
        print("\n最近 3 条：")
        for s in m["sessions"][-3:]:
            print("  %s [%s] 状态=%s 预警=%d"
                  % (s.get("record_id"), s.get("source"), s.get("mental_state"),
                     len(s.get("alerts") or [])))
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="MedSignal 真实公开 EEG 数据集接入")
    parser.add_argument("--source", choices=["demo", "local", "physionet", "eegemotions27"],
                        default="demo", help="数据源")
    parser.add_argument("--dir", help="local 模式的 EEG 文件目录")
    parser.add_argument("--subjects", default="S001",
                        help="physionet 模式：受试者（逗号分隔，如 S001,S002）")
    parser.add_argument("--runs", default="1,2",
                        help="physionet 模式：run 编号（1/2=基线，3/4=运动任务）")
    parser.add_argument("--pairs", default="",
                        help="eegemotions27 模式：受试者:情绪ID（逗号分隔，如 10:5,10:17；"
                             "缺省为受试者10的 anger/fear/joy/calmness/sadness 五情绪样本）")
    parser.add_argument("--limit", type=int, default=10, help="local 模式最多导入数（0=不限）")
    parser.add_argument("--list", action="store_true", help="仅查看 manifest 概览")
    args = parser.parse_args()

    if args.list:
        print_summary()
        return 0

    entries = []
    if args.source == "local":
        if not args.dir:
            log.error("--source local 需要 --dir 指定 EEG 文件目录")
            return 1
        entries = source_local(args.dir, args.limit)
    elif args.source == "physionet":
        subjects = [s for s in args.subjects.split(",") if s.strip()]
        runs = [int(r) for r in args.runs.split(",") if r.strip()]
        entries = source_physionet(subjects, runs)
    elif args.source == "eegemotions27":
        if args.pairs:
            pairs = [tuple(int(x) for x in p.split(":"))
                     for p in args.pairs.split(",") if ":" in p]
        else:
            pairs = EEGEMOTIONS27_DEFAULT_PAIRS
        entries = source_eegemotions27(pairs)
    elif args.source == "demo":
        entries = source_demo()

    if not entries:
        log.warning("没有导入任何 EEG 记录")
        return 1

    merge_into_manifest(args.source, entries)
    print_summary()
    log.info("完成：%d 条真实 EEG 评估已入库。", len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
