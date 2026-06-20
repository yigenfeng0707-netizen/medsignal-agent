"""医保智脑 - 脑电健康引擎（EEG Engine）

BCI×医保创新核心模块，提供 EEG 信号生成、频域特征提取、
健康指标计算、异常预警、医保政策联动全链路能力。
"""

from app.services.eeg.engine import (
    EEGSession,
    MENTAL_STATES,
    SAMPLE_RATE,
    CHANNELS,
    BANDS,
    assess_session,
    compute_health_metrics,
    extract_band_powers,
    generate_synthetic_eeg,
    link_to_policies,
    pick_mental_state_by_profile,
    realtime_stream,
    scan_eeg_alerts,
)

__all__ = [
    "EEGSession",
    "MENTAL_STATES",
    "SAMPLE_RATE",
    "CHANNELS",
    "BANDS",
    "assess_session",
    "compute_health_metrics",
    "extract_band_powers",
    "generate_synthetic_eeg",
    "link_to_policies",
    "pick_mental_state_by_profile",
    "realtime_stream",
    "scan_eeg_alerts",
]
