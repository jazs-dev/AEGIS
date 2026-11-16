"""Streamlit-independent ECG validation, preprocessing and feature extraction.

The implementation is an experimental signal-processing layer.  It preserves
the input samples and keeps quality assessment separate from rhythm labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy import signal

from src.processing.config_loader import default_config_directory


class ECGProcessingError(ValueError):
    """Raised when an ECG contract or processing parameter is invalid."""


@dataclass(frozen=True)
class ECGSignal:
    """Input ECG contract with an immutable copy of the original samples."""

    samples: np.ndarray
    sampling_rate_hz: float
    amplitude_unit: str
    start_time: datetime | str | None = None
    record_id: str = ""
    source: str = "synthetic"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            array = np.asarray(self.samples, dtype=float).reshape(-1).copy()
        except (TypeError, ValueError) as exc:
            raise ECGProcessingError("ECG samples must be numeric") from exc
        array.setflags(write=False)
        object.__setattr__(self, "samples", array)
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True)
class ECGValidation:
    """Validation and quantifiable signal-quality observations."""

    valid: bool
    status: str
    reason: str
    missing_samples_ratio: float
    clipping_ratio: float
    noise_ratio: float
    signal_std: float


@dataclass(frozen=True)
class ECGProcessed:
    """Processed window retaining raw data, filtered data and features."""

    signal: ECGSignal
    raw_samples: np.ndarray
    filtered_samples: np.ndarray
    validation: ECGValidation
    ecg_quality: str
    features: Mapping[str, float]


def load_ecg_parameters(config_directory: str | Path | None = None) -> dict[str, Any]:
    """Load the separate experimental ECG parameter document."""
    directory = Path(config_directory) if config_directory is not None else default_config_directory()
    path = directory / "ecg_algorithm_parameters.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ECGProcessingError(f"Unable to read ECG parameter file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ECGProcessingError(f"Invalid ECG parameter JSON at line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(document, dict):
        raise ECGProcessingError("ECG parameter document must be an object")
    return document


def validate_ecg_signal(ecg: ECGSignal, parameters: Mapping[str, Any] | None = None) -> ECGValidation:
    """Validate numeric samples, units, rate, length, missingness and noise."""
    params = parameters or load_ecg_parameters()
    samples = ecg.samples
    if ecg.amplitude_unit not in {"mV", "V"}:
        return _invalid("amplitude_unit must be explicitly 'mV' or 'V'")
    if not np.isfinite(ecg.sampling_rate_hz) or ecg.sampling_rate_hz < params["sampling"]["minimum_sampling_rate_hz"]:
        return _invalid("sampling_rate_hz is below the configured processing minimum")
    if samples.size < int(np.ceil(ecg.sampling_rate_hz * params["sampling"]["window_seconds"])):
        return _invalid("signal is shorter than the configured analysis window")
    missing = float(np.count_nonzero(~np.isfinite(samples)) / samples.size)
    analysis_samples = _samples_in_millivolts(ecg)
    finite = analysis_samples[np.isfinite(analysis_samples)]
    if not finite.size:
        return _invalid("signal contains no finite samples", missing=missing)
    clipping = _clipping_ratio(ecg, finite)
    filled = _interpolate_missing(analysis_samples)
    centered = filled - np.mean(filled)
    std = float(np.std(centered))
    noise = _high_frequency_noise_ratio(centered, ecg.sampling_rate_hz)
    quality = params["quality"]
    if missing > quality["max_missing_samples_ratio"]:
        return _invalid("missing sample ratio exceeds experimental quality limit", missing, clipping, noise, std)
    if clipping > quality["max_clipping_ratio"]:
        return _invalid("clipping ratio exceeds experimental quality limit", missing, clipping, noise, std)
    if std < quality["minimum_signal_std"]:
        return _invalid("signal amplitude is insufficient for interpretation", missing, clipping, noise, std)
    if noise > quality["max_high_frequency_noise_ratio"]:
        return _invalid("high-frequency noise ratio exceeds experimental quality limit", missing, clipping, noise, std)
    return ECGValidation(True, "valid", "signal passed experimental quality checks", missing, clipping, noise, std)


def filter_ecg(ecg: ECGSignal, parameters: Mapping[str, Any] | None = None) -> np.ndarray:
    """Return a broad analysis-band, zero-phase filtered copy of the ECG."""
    params = parameters or load_ecg_parameters()
    validation = validate_ecg_signal(ecg, params)
    if not validation.valid:
        raise ECGProcessingError(validation.reason)
    samples = _interpolate_missing(_samples_in_millivolts(ecg))
    low, high = params["preprocessing"]["analysis_bandpass_hz"]
    if high >= ecg.sampling_rate_hz / 2:
        raise ECGProcessingError("analysis upper cutoff must be below Nyquist frequency")
    sos = signal.butter(params["preprocessing"]["analysis_filter_order"], [low, high], btype="bandpass", fs=ecg.sampling_rate_hz, output="sos")
    return signal.sosfiltfilt(sos, samples)


def segment_ecg(ecg: ECGSignal, window_seconds: float, step_seconds: float | None = None) -> tuple[ECGSignal, ...]:
    """Split an ECG into deterministic overlapping windows without changing samples."""
    if window_seconds <= 0 or (step_seconds is not None and step_seconds <= 0):
        raise ECGProcessingError("window_seconds and step_seconds must be positive")
    step = step_seconds or window_seconds
    width = int(round(window_seconds * ecg.sampling_rate_hz))
    advance = int(round(step * ecg.sampling_rate_hz))
    if width <= 0 or advance <= 0:
        raise ECGProcessingError("window is smaller than one sample")
    return tuple(
        ECGSignal(ecg.samples[start : start + width], ecg.sampling_rate_hz, ecg.amplitude_unit, ecg.start_time, f"{ecg.record_id}:{start}", ecg.source, ecg.metadata)
        for start in range(0, max(0, ecg.samples.size - width + 1), advance)
    )


def extract_ecg_features(ecg: ECGSignal, filtered_samples: np.ndarray | None = None, parameters: Mapping[str, Any] | None = None) -> dict[str, float]:
    """Calculate reproducible amplitude, spectral and threshold-crossing features."""
    params = parameters or load_ecg_parameters()
    validation = validate_ecg_signal(ecg, params)
    if not validation.valid:
        raise ECGProcessingError(validation.reason)
    samples = np.asarray(filtered_samples if filtered_samples is not None else filter_ecg(ecg, params), dtype=float)
    centered = samples - np.mean(samples)
    n = centered.size
    freqs = np.fft.rfftfreq(n, 1.0 / ecg.sampling_rate_hz)
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(n))) ** 2
    total = float(np.sum(spectrum[1:])) or 1.0
    vf_low, vf_high = params["vf"]["analysis_band_hz"]
    vf_power = float(np.sum(spectrum[(freqs >= vf_low) & (freqs <= vf_high)]))
    probabilities = spectrum[1:] / total
    entropy = float(-np.sum(probabilities * np.log2(probabilities + 1e-12)) / np.log2(max(2, probabilities.size)))
    crossings = np.flatnonzero(np.diff(np.signbit(centered)))
    crossing_intervals = np.diff(crossings) / ecg.sampling_rate_hz if crossings.size > 1 else np.array([])
    tci_mean = float(np.mean(crossing_intervals)) if crossing_intervals.size else float("nan")
    tci_cv = float(np.std(crossing_intervals) / np.mean(crossing_intervals)) if crossing_intervals.size and np.mean(crossing_intervals) else float("nan")
    dominant = int(np.argmax(spectrum[1:]) + 1) if spectrum.size > 1 else 0
    return {
        "rms": float(np.sqrt(np.mean(centered**2))),
        "energy": float(np.sum(centered**2)),
        "dominant_frequency_hz": float(freqs[dominant]),
        "spectral_entropy": entropy,
        "vf_band_power_ratio": vf_power / total,
        "tci_mean_seconds": tci_mean,
        "tci_cv": tci_cv,
        "missing_samples_ratio": validation.missing_samples_ratio,
        "clipping_ratio": validation.clipping_ratio,
        "noise_ratio": validation.noise_ratio,
    }


def process_ecg(ecg: ECGSignal, parameters: Mapping[str, Any] | None = None) -> ECGProcessed:
    """Validate, filter and extract features while preserving the raw signal."""
    params = parameters or load_ecg_parameters()
    validation = validate_ecg_signal(ecg, params)
    raw = ecg.samples.copy()
    raw.setflags(write=False)
    if not validation.valid:
        return ECGProcessed(ecg, raw, np.array([], dtype=float), validation, "invalid", {})
    filtered = filter_ecg(ecg, params)
    features = extract_ecg_features(ecg, filtered, params)
    return ECGProcessed(ecg, raw, filtered, validation, "valid", features)


def _invalid(reason: str, missing: float = 0.0, clipping: float = 0.0, noise: float = 0.0, std: float = 0.0) -> ECGValidation:
    return ECGValidation(False, "invalid", reason, missing, clipping, noise, std)


def _interpolate_missing(samples: np.ndarray) -> np.ndarray:
    values = np.asarray(samples, dtype=float).copy()
    finite = np.isfinite(values)
    if finite.all():
        return values
    if not finite.any():
        return values
    indexes = np.arange(values.size)
    values[~finite] = np.interp(indexes[~finite], indexes[finite], values[finite])
    return values


def _samples_in_millivolts(ecg: ECGSignal) -> np.ndarray:
    """Return a working copy in mV while leaving the declared raw unit intact."""
    samples = np.asarray(ecg.samples, dtype=float)
    return samples * 1000.0 if ecg.amplitude_unit == "V" else samples.copy()


def _clipping_ratio(ecg: ECGSignal, samples: np.ndarray) -> float:
    low, high = ecg.metadata.get("adc_min"), ecg.metadata.get("adc_max")
    if low is None or high is None or high <= low:
        return 0.0
    return float(np.mean((samples <= low) | (samples >= high)))


def _high_frequency_noise_ratio(samples: np.ndarray, sampling_rate_hz: float) -> float:
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(samples.size))) ** 2
    frequencies = np.fft.rfftfreq(samples.size, 1.0 / sampling_rate_hz)
    total = float(np.sum(spectrum)) or 1.0
    return float(np.sum(spectrum[frequencies > min(30.0, sampling_rate_hz / 3)]) / total)
