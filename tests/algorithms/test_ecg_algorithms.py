from __future__ import annotations

import numpy as np
from scipy import signal

from src.algorithms.qrs_detection import detect_qrs
from src.algorithms.vf_detection import classify_ecg
from src.processing.ecg_processing import ECGSignal, process_ecg


def organized_signal(fs: float = 250.0, seconds: float = 8.0) -> np.ndarray:
    t = np.arange(int(fs * seconds)) / fs
    result = np.zeros_like(t)
    for beat in np.arange(0.5, seconds, 1.0):
        result += 1.2 * np.exp(-((t - beat) / 0.025) ** 2)
        result -= 0.2 * np.exp(-((t - beat - 0.08) / 0.04) ** 2)
    return result


def vf_like_signal(seed: int = 7, fs: float = 250.0, seconds: float = 8.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    samples = rng.normal(size=int(fs * seconds))
    sos = signal.butter(4, [3.0, 12.0], btype="bandpass", fs=fs, output="sos")
    samples = signal.sosfiltfilt(sos, samples)
    return samples / np.std(samples) * 0.1


def make_ecg(samples: np.ndarray) -> ECGSignal:
    return ECGSignal(samples, 250.0, "mV", "2026-01-01T00:00:00+00:00", "synthetic", "synthetic")


def test_qrs_detection_finds_organized_candidates() -> None:
    processed = process_ecg(make_ecg(organized_signal()))
    qrs = detect_qrs(processed)
    assert len(qrs.positions) >= 3
    assert qrs.qrs_status in {"organized", "abnormal"}
    assert all(interval > 0 for interval in qrs.rr_intervals_seconds)
    assert classify_ecg(processed, qrs).rhythm_classification == "normal_sinus"


def test_vf_classifier_uses_positive_signal_evidence_not_qrs_absence_alone() -> None:
    processed = process_ecg(make_ecg(vf_like_signal()))
    qrs = detect_qrs(processed)
    result = classify_ecg(processed, qrs)
    assert result.ecg_quality == "valid"
    assert result.qrs_status in {"not_organized", "uninterpretable"}
    assert result.rhythm_classification in {"vf_compatible", "uninterpretable", "abnormal_non_vf"}
    assert result.features["rms"] > 0


def test_zero_qrs_on_constant_signal_does_not_become_vf() -> None:
    processed = process_ecg(make_ecg(np.zeros(2000)))
    qrs = detect_qrs(processed)
    result = classify_ecg(processed, qrs)
    assert result.rhythm_classification != "vf_compatible"


def test_classifier_is_reproducible() -> None:
    samples = vf_like_signal()
    first = classify_ecg(process_ecg(make_ecg(samples)), detect_qrs(process_ecg(make_ecg(samples))))
    second = classify_ecg(process_ecg(make_ecg(samples)), detect_qrs(process_ecg(make_ecg(samples))))
    assert first == second
