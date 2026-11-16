"""Deterministic, experimental spectral VF-pattern classifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.algorithms.qrs_detection import QRSDetectionResult
from src.processing.ecg_processing import ECGProcessed, load_ecg_parameters


@dataclass(frozen=True)
class VFDetectionResult:
    """ECG categories plus the features and rationale used to produce them."""

    ecg_quality: str
    qrs_status: str
    rhythm_classification: str
    vf_score: float | None
    explanation: str
    features: Mapping[str, float]

    def categories(self) -> dict[str, str]:
        """Return categories compatible with ``monitor.py``."""
        return {"ecg_quality": self.ecg_quality, "qrs_status": self.qrs_status, "rhythm_classification": self.rhythm_classification}


def classify_ecg(processed: ECGProcessed, qrs: QRSDetectionResult, parameters: Mapping[str, Any] | None = None) -> VFDetectionResult:
    """Classify quality, QRS organization and rhythm using configured features.

    ``vf_compatible`` requires positive spectral activity evidence and a
    non-organized QRS result; absence of QRS candidates alone is insufficient.
    """
    params = parameters or load_ecg_parameters()
    if processed.ecg_quality != "valid":
        return VFDetectionResult("invalid", "uninterpretable", "uninterpretable", None, processed.validation.reason, {})
    features = dict(processed.features)
    vf = params["vf"]
    band = min(1.0, features.get("vf_band_power_ratio", 0.0) / max(vf["minimum_band_power_ratio"], 1e-12))
    entropy = min(1.0, features.get("spectral_entropy", 0.0) / max(vf["minimum_spectral_entropy"], 1e-12))
    tci = features.get("tci_cv", 0.0)
    irregularity = 0.0 if tci != tci else min(1.0, tci)
    weights = vf["weights"]
    score = float(weights["band_power_ratio"] * band + weights["spectral_entropy"] * entropy + weights["temporal_crossing_irregularity"] * irregularity)
    features["vf_score"] = score
    if (
        qrs.qrs_status == "organized"
        and qrs.confidence > 0
        and qrs.rr_intervals_seconds
        and features.get("spectral_entropy", 1.0) <= vf["normal_sinus_max_spectral_entropy"]
    ):
        rhythm = "normal_sinus"
        return VFDetectionResult("valid", qrs.qrs_status, rhythm, score, "Organized QRS, regular RR evidence and concentrated spectrum", features)
    if qrs.qrs_status == "not_organized" and features["rms"] >= vf["minimum_activity_rms"] and score >= vf["vf_score_threshold"]:
        return VFDetectionResult("valid", qrs.qrs_status, "vf_compatible", score, "Positive spectral/temporal activity and non-organized QRS evidence", features)
    if not qrs.interpretable:
        return VFDetectionResult("valid", qrs.qrs_status, "uninterpretable", score, "ECG quality is valid but rhythm organization is inconclusive", features)
    return VFDetectionResult("valid", qrs.qrs_status, "abnormal_non_vf", score, "Interpretable rhythm does not satisfy the experimental VF decision", features)
