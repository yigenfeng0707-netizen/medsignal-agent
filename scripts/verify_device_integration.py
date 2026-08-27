"""EEG 设备接入端到端验证脚本

验证流程：
1. 后端服务健康检查
2. 设备检查端点 GET /api/eeg/device/check
3. CSV 文件导入端点 POST /api/eeg/{user_id}/import
4. 合成信号端点 POST /api/eeg/{user_id}/session（回归测试）
5. 真实设备端点 POST /api/eeg/{user_id}/session-device（无设备时优雅失败）
6. 引擎层 assess_real_session 直接调用（不依赖 HTTP）

使用方法：
    # 默认测试本地后端 http://localhost:8000
    python scripts/verify_device_integration.py

    # 指定后端地址
    python scripts/verify_device_integration.py --api-base http://192.168.1.100:8000

    # 仅运行引擎层测试（不需要后端启动）
    python scripts/verify_device_integration.py --engine-only

    # 生成测试 CSV 文件并保留
    python scripts/verify_device_integration.py --save-csv test_eeg.csv
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

# 添加 backend 到 path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np


# ============================================================
# 测试用 CSV 生成
# ============================================================

def generate_test_csv(
    n_samples: int = 1024,
    sample_rate: int = 256,
    mental_state: str = "relaxed",
) -> str:
    """生成测试用 CSV 内容。

    Args:
        n_samples: 采样点数
        sample_rate: 采样率
        mental_state: relaxed（高 α）/ stressed（高 β）/ focused（平衡）

    Returns:
        CSV 字符串
    """
    t = np.arange(n_samples) / sample_rate
    rng = np.random.default_rng(42)

    if mental_state == "relaxed":
        alpha_amp, beta_amp = 30, 5
    elif mental_state == "stressed":
        alpha_amp, beta_amp = 5, 30
    elif mental_state == "focused":
        alpha_amp, beta_amp = 15, 15
    else:
        alpha_amp, beta_amp = 20, 10

    channels = ["TP9", "AF7", "AF8", "TP10"]
    lines = [",".join(channels)]
    # 每通道使用固定相位，保证频谱峰值清晰
    channel_phases = [0.0, 0.5, 1.0, 1.5]
    channel_data = []
    for ci, _ in enumerate(channels):
        phase = channel_phases[ci]
        alpha = alpha_amp * np.sin(2 * np.pi * 10 * t + phase)
        beta = beta_amp * np.sin(2 * np.pi * 20 * t + phase * 1.3)
        noise = rng.normal(0, 5, n_samples)
        channel_data.append(alpha + beta + noise)
    for i in range(n_samples):
        vals = [channel_data[ci][i] for ci in range(len(channels))]
        lines.append(",".join(f"{v:.4f}" for v in vals))
    return "\n".join(lines)


# ============================================================
# 引擎层验证（不依赖 HTTP）
# ============================================================

def verify_engine_layer() -> bool:
    """验证引擎层 assess_real_session 和 device_adapter 正常工作。

    Returns:
        True 表示全部通过
    """
    print("\n" + "=" * 60)
    print("【第 1 步】引擎层验证（不依赖 HTTP 后端）")
    print("=" * 60)

    all_passed = True

    # 1.1 device_adapter.from_numpy
    print("\n  [1.1] device_adapter.from_numpy ...", end=" ")
    try:
        from app.services.eeg.device_adapter import from_numpy, load_from_csv
        rng = np.random.default_rng(42)
        signals = [rng.normal(0, 20, 1024) for _ in range(4)]
        sigs, chs, sr, info = from_numpy(signals, sample_rate=256)
        assert len(sigs) == 4
        assert chs == ["TP9", "AF7", "AF8", "TP10"]
        assert info.source == "numpy"
        print(f"✓ 通过（{len(sigs)} 通道 × {len(sigs[0])} 点, 质量={info.signal_quality}）")
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 1.2 device_adapter.load_from_csv
    print("  [1.2] device_adapter.load_from_csv ...", end=" ")
    try:
        csv_content = generate_test_csv(mental_state="relaxed")
        sigs, chs, sr, info = load_from_csv(csv_content, sample_rate=256, filename="test.csv")
        assert len(sigs) == 4
        assert info.source == "csv"
        assert info.duration_seconds == 4.0
        print(f"✓ 通过（{len(sigs)} 通道 × {len(sigs[0])} 点, 质量={info.signal_quality}）")
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 1.3 engine.assess_real_session（auto 推断）
    print("  [1.3] engine.assess_real_session（auto 推断）...", end=" ")
    try:
        from app.services.eeg.engine import assess_real_session
        csv_content = generate_test_csv(mental_state="relaxed")
        sigs, chs, sr, info = load_from_csv(csv_content, sample_rate=256)
        session = assess_real_session(
            user_id="test_user",
            signals=sigs,
            channels=chs,
            sample_rate=sr,
            mental_state="auto",
            device_info=info.to_dict(),
        )
        assert session.source == "file"
        assert session.mental_state in ("relaxed", "focused", "stressed", "fatigued", "sleep_deprived")
        assert 0 <= session.metrics["stress_index"] <= 100
        print(f"✓ 通过（推断状态={session.mental_state_label}, 压力={session.metrics['stress_index']:.1f}）")
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 1.4 高压力信号触发预警
    print("  [1.4] 高压力信号触发预警 ...", end=" ")
    try:
        from app.services.eeg.engine import assess_real_session
        csv_content = generate_test_csv(mental_state="stressed")
        sigs, chs, sr, info = load_from_csv(csv_content, sample_rate=256)
        session = assess_real_session(
            user_id="test_user",
            signals=sigs,
            channels=chs,
            sample_rate=sr,
            mental_state="stressed",
            device_info=info.to_dict(),
        )
        assert len(session.alerts) > 0, "高压力信号应触发预警"
        print(f"✓ 通过（触发 {len(session.alerts)} 条预警）")
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    return all_passed


# ============================================================
# HTTP API 验证
# ============================================================

def verify_http_api(api_base: str, save_csv: str | None = None) -> bool:
    """验证 HTTP API 端点。

    Args:
        api_base: 后端 API 基础地址
        save_csv: 若指定，将测试 CSV 保存到此路径

    Returns:
        True 表示全部通过
    """
    print("\n" + "=" * 60)
    print(f"【第 2 步】HTTP API 验证（后端：{api_base}）")
    print("=" * 60)

    try:
        import requests
    except ImportError:
        print("  ✗ 跳过：未安装 requests 库（pip install requests）")
        return False

    all_passed = True
    user_id = "verify_user"
    session = requests.Session()

    # 2.1 健康检查
    print("\n  [2.1] GET /api/health ...", end=" ")
    try:
        r = session.get(f"{api_base}/api/health", timeout=10)
        if r.ok:
            print(f"✓ 通过（{r.json().get('status', 'ok')}）")
        else:
            print(f"✗ 失败：HTTP {r.status_code}")
            all_passed = False
    except Exception as e:
        print(f"✗ 失败：{e}")
        print("    请确认后端已启动：cd backend && uvicorn app.main:app --reload")
        return False

    # 2.2 设备检查
    print("  [2.2] GET /api/eeg/device/check ...", end=" ")
    try:
        r = session.get(f"{api_base}/api/eeg/device/check", timeout=15)
        if r.ok:
            data = r.json()
            connected = data.get("connected", False)
            pylsl = data.get("pylsl_installed", False)
            print(f"✓ 通过（pylsl_installed={pylsl}, connected={connected}）")
            if not pylsl:
                print("    提示：后端未安装 pylsl，真实设备采集将不可用。安装：pip install pylsl")
            if not connected:
                print("    提示：未检测到 LSL 流。如需测试真实设备，请先启动 muselsl stream")
        else:
            print(f"✗ 失败：HTTP {r.status_code}")
            all_passed = False
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 2.3 合成信号采集（回归测试）
    print("  [2.3] POST /api/eeg/{user_id}/session（合成信号）...", end=" ")
    try:
        r = session.post(
            f"{api_base}/api/eeg/{user_id}/session",
            params={"mental_state": "relaxed", "duration_seconds": 4},
            timeout=30,
        )
        if r.ok:
            data = r.json()
            assert "session_id" in data
            assert "metrics" in data
            print(f"✓ 通过（session_id={data['session_id'][:20]}..., 压力={data['metrics']['stress_index']:.1f}）")
        else:
            print(f"✗ 失败：HTTP {r.status_code} - {r.text[:200]}")
            all_passed = False
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 2.4 CSV 文件导入
    print("  [2.4] POST /api/eeg/{user_id}/import（CSV 导入）...", end=" ")
    try:
        csv_content = generate_test_csv(mental_state="relaxed")
        if save_csv:
            Path(save_csv).write_text(csv_content, encoding="utf-8")
            print(f"\n    测试 CSV 已保存到：{save_csv}")

        files = {"file": ("test_eeg.csv", csv_content.encode("utf-8"), "text/csv")}
        r = session.post(
            f"{api_base}/api/eeg/{user_id}/import",
            params={"sample_rate": 256, "mental_state": "auto"},
            files=files,
            timeout=30,
        )
        if r.ok:
            data = r.json()
            assert "session_id" in data
            source = data.get("source", "unknown")
            mental_state = data.get("mental_state", "unknown")
            print(f"✓ 通过（source={source}, 推断状态={mental_state}）")
        else:
            print(f"✗ 失败：HTTP {r.status_code} - {r.text[:200]}")
            all_passed = False
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    # 2.5 真实设备采集（无设备时应优雅失败）
    print("  [2.5] POST /api/eeg/{user_id}/session-device（真实设备）...", end=" ")
    try:
        r = session.post(
            f"{api_base}/api/eeg/{user_id}/session-device",
            params={"duration_seconds": 2, "mental_state": "auto"},
            timeout=20,
        )
        if r.ok:
            data = r.json()
            print(f"✓ 通过（真实设备采集成功！session_id={data['session_id'][:20]}...）")
        elif r.status_code == 503:
            print(f"✓ 预期失败（无设备/pylsl 未装）：{r.json().get('detail', '')[:80]}")
        else:
            print(f"✗ 异常：HTTP {r.status_code} - {r.text[:200]}")
            all_passed = False
    except Exception as e:
        print(f"✗ 失败：{e}")
        all_passed = False

    return all_passed


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="EEG 设备接入端到端验证")
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000",
        help="后端 API 基础地址（默认 http://localhost:8000）",
    )
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="仅运行引擎层验证（不需要后端启动）",
    )
    parser.add_argument(
        "--save-csv",
        default=None,
        help="将测试 CSV 保存到指定路径",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  医保智脑 · EEG 设备接入端到端验证")
    print("=" * 60)
    print(f"  时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  后端：{args.api_base if not args.engine_only else '（跳过 HTTP）'}")

    # 引擎层验证
    engine_ok = verify_engine_layer()

    # HTTP API 验证
    http_ok = True
    if not args.engine_only:
        http_ok = verify_http_api(args.api_base, args.save_csv)

    # 汇总
    print("\n" + "=" * 60)
    print("  验证汇总")
    print("=" * 60)
    print(f"  引擎层：{'✓ 全部通过' if engine_ok else '✗ 存在失败'}")
    if not args.engine_only:
        print(f"  HTTP API：{'✓ 全部通过' if http_ok else '✗ 存在失败'}")
    print("=" * 60)

    if engine_ok and (args.engine_only or http_ok):
        print("\n  ✓ 所有验证通过！EEG 设备接入功能正常。")
        print("\n  下一步：")
        print("    1. 启动前端：cd frontend && npm run dev")
        print("    2. 打开 http://localhost:3000/eeg")
        print("    3. 切换到「真实设备」或「文件导入」模式开始测试")
        print("    4. 真实设备需先启动 LSL 流（如 muselsl stream）")
        sys.exit(0)
    else:
        print("\n  ✗ 存在失败项，请根据上述提示排查。")
        sys.exit(1)


if __name__ == "__main__":
    main()
