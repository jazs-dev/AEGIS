from __future__ import annotations

from datetime import datetime, timezone

from src.algorithms.qrs_detection import detect_qrs
from src.algorithms.vf_detection import classify_ecg
from src.monitoring.monitor import Monitor
from src.processing.ecg_processing import ECGSignal, process_ecg
from tests.algorithms.test_ecg_algorithms import vf_like_signal


def test_samples_to_processing_to_rules_and_state_machine() -> None:
    ecg = ECGSignal(vf_like_signal(), 250.0, "mV", "2026-01-01T00:00:00+00:00", "vf-synthetic", "synthetic")
    processed = process_ecg(ecg)
    qrs = detect_qrs(processed)
    classification = classify_ecg(processed, qrs)
    categories = {
        "heart_rate_status": "not_reliably_calculable",
        "spo2_status": "not_assessed",
        "respiratory_rate_status": "not_assessed",
        "blood_pressure_status": "not_assessed",
        "ecg_quality": classification.ecg_quality,
        "qrs_status": classification.qrs_status,
        "rhythm_classification": classification.rhythm_classification,
        "pulse_status": "not_assessed",
        "responsiveness_status": "not_assessed",
        "breathing_status": "not_assessed",
    }
    result = Monitor().evaluate(categories, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert classification.rhythm_classification == "vf_compatible"
    assert result.candidate_state == "SUSPECTED_VF"
    assert result.effective_state == "SUSPECTED_VF"
    assert result.rule_decision is not None and result.rule_decision.rule_id == "R02"
