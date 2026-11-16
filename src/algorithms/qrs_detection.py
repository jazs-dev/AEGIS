"""Deterministic Pan-Tompkins-inspired QRS candidate detection.

This is an engineering variant for experimentation, not a clinical detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from scipy import signal

from src.processing.ecg_processing import ECGProcessingError, ECGProcessed, load_ecg_parameters


@dataclass(frozen=True)
class QRSDetectionResult:
    """Quantitative QRS result and conservative organization category."""

    positions: tuple[int, ...]
    rr_intervals_seconds: tuple[float, ...]
    confidence: float
    organization_score: float
    qrs_status: str
    interpretable: bool
    explanation: str


def detect_qrs(processed: ECGProcessed, parameters: Mapping[str, Any] | None = None) -> QRSDetectionResult:
    """Detect QRS candidates and classify organization without inferring VF."""
    params = parameters or load_ecg_parameters()
    if processed.ecg_quality != "valid":
        return QRSDetectionResult((), (), 0.0, 0.0, "uninterpretable", False, "ECG quality is not valid")
    ecg = processed.signal
    low, high = params["preprocessing"]["qrs_bandpass_hz"]
    if high >= ecg.sampling_rate_hz / 2:
        raise ECGProcessingError("QRS upper cutoff must be below Nyquist frequency")
    sos = signal.butter(params["preprocessing"]["qrs_filter_order"], [low, high], btype="bandpass", fs=ecg.sampling_rate_hz, output="sos")
    band = signal.sosfiltfilt(sos, processed.raw_samples if np.isfinite(processed.raw_samples).all() else np.nan_to_num(processed.raw_samples))
    differentiated = np.diff(band, prepend=band[0])
    squared = differentiated**2
    width = max(1, int(round(params["qrs"]["integration_window_seconds"] * ecg.sampling_rate_hz)))
    integrated = np.convolve(squared, np.ones(width) / width, mode="same")
    threshold = float(np.mean(integrated) + params["qrs"]["threshold_scale"] * np.std(integrated))
    distance = max(1, int(round(params["qrs"]["minimum_peak_distance_seconds"] * ecg.sampling_rate_hz)))
    peaks, properties = signal.find_peaks(integrated, height=threshold, distance=distance)
    rr = np.diff(peaks) / ecg.sampling_rate_hz
    score = _organization_score(processed.filtered_samples, ecg.sampling_rate_hz)
    confidence = float(min(1.0, len(peaks) / max(1, params["qrs"]["minimum_organized_beats"])) * min(1.0, np.std(integrated) / (np.mean(integrated) + 1e-12)))
    if len(peaks) >= params["qrs"]["minimum_organized_beats"]:
        rr_cv = float(np.std(rr) / np.mean(rr)) if rr.size and np.mean(rr) else float("inf")
        if rr_cv <= params["qrs"]["organized_rr_cv_max"]:
            status = "organized"
        elif rr_cv >= params["qrs"]["not_organized_rr_cv_min"]:
            status = "not_organized"
        else:
            status = "abnormal"
        return QRSDetectionResult(tuple(map(int, peaks)), tuple(map(float, rr)), confidence, score, status, True, f"Detected {len(peaks)} QRS candidates; RR CV={rr_cv:.3f}")
    if score <= params["qrs"]["not_organized_score_max"] and np.sqrt(np.mean(processed.filtered_samples**2)) >= params["qrs"]["minimum_activity_rms"]:
        return QRSDetectionResult(tuple(map(int, peaks)), tuple(map(float, rr)), confidence, score, "not_organized", True, "Signal is active and interpretable but lacks organized QRS evidence")
    return QRSDetectionResult(tuple(map(int, peaks)), tuple(map(float, rr)), confidence, score, "uninterpretable", False, "Insufficient evidence to characterize ventricular organization")


def _organization_score(samples: np.ndarray, sampling_rate_hz: float) -> float:
    centered = samples - np.mean(samples)
    if np.std(centered) == 0:
        return 0.0
    max_lag = min(centered.size // 2, int(round(sampling_rate_hz * 1.5)))
    autocorrelation = signal.fftconvolve(centered, centered[::-1], mode="full")[centered.size - 1 : centered.size + max_lag]
    autocorrelation /= autocorrelation[0] or 1.0
    return float(np.clip(np.max(autocorrelation[1:]) if autocorrelation.size > 1 else 0.0, 0.0, 1.0))
