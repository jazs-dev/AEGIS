from __future__ import annotations

import numpy as np

from src.evaluation.vf_evaluator import SegmentEvaluation, compute_metrics, save_report, evaluate_record, compute_temporal_summary
from src.evaluation.reporting import write_figures
from src.datasets.physionet_loader import DATASETS, PhysioNetRecord
from src.datasets.rhythm_annotations import parse_annotation_rows
from src.processing.ecg_processing import ECGSignal


def result(reference: str, prediction: str, abstained: bool = False) -> SegmentEvaluation:
    return SegmentEvaluation("vfdb", "fixture", 0, 1000, 0.0, 4.0, reference, reference, prediction, "uninterpretable" if abstained else prediction.lower(), "valid", abstained, True, None, {"vf_score": 0.5})


def test_confusion_metrics_and_safe_division() -> None:
    metrics = compute_metrics((result("VF", "VF"), result("VF", "NON_VF"), result("NON_VF", "VF"), result("NON_VF", "NON_VF")))
    assert metrics.confusion.tp == 1
    assert metrics.confusion.fp == 1
    assert metrics.confusion.tn == 1
    assert metrics.confusion.fn == 1
    assert metrics.sensitivity == 0.5
    assert metrics.specificity == 0.5
    assert metrics.precision == 0.5
    assert metrics.f1 == 0.5
    assert metrics.accuracy == 0.5
    assert compute_metrics((result("VF", "ABSTAIN", True),)).sensitivity is None


def test_vf_abstention_can_be_counted_as_false_negative() -> None:
    metrics = compute_metrics((result("VF", "ABSTAIN", True),), count_vf_abstentions_as_fn=True)
    assert metrics.confusion.fn == 1
    assert metrics.sensitivity == 0.0
    assert metrics.abstentions == 1


def test_evaluator_runs_existing_detector_on_fixture_record(tmp_path) -> None:
    samples = np.sin(np.arange(2000) / 250 * 2 * np.pi)
    record = PhysioNetRecord(DATASETS["vfdb"], "fixture", ECGSignal(samples, 250, "mV", record_id="fixture", source="fixture"), 0, "ECG", "mV", 2000, parse_annotation_rows(((0, "NSR"),), "vfdb"))
    evaluated = evaluate_record(record, window_seconds=4)
    assert evaluated
    assert all(item.record_id == "fixture" for item in evaluated)
    assert all(item.reference_label == "NON_VF" for item in evaluated)


def test_report_and_figures_are_reproducible_artifacts(tmp_path) -> None:
    from src.evaluation.vf_evaluator import EvaluationReport, Metrics, ConfusionMatrix

    segments = (result("VF", "VF"), result("NON_VF", "NON_VF"))
    metrics = compute_metrics(segments)
    report = EvaluationReport({"real_ecg_metrics": False}, segments, metrics, metrics, {"vfdb": metrics}, {"vfdb:fixture": metrics}, {"VF": metrics, "NSR": metrics}, {"valid": metrics}, compute_temporal_summary(segments))
    json_path, csv_path = save_report(report, tmp_path)
    figures = write_figures(report, tmp_path)
    assert json_path.is_file() and csv_path.is_file()
    assert all(path.is_file() for path in figures)


def test_temporal_summary_uses_end_of_window_as_detection_availability() -> None:
    segments = (
        SegmentEvaluation("vfdb", "fixture", 0, 1000, 0.0, 4.0, "VF", "VF", "NON_VF", "abnormal_non_vf", "valid", False, True, None, {}),
        SegmentEvaluation("vfdb", "fixture", 1000, 2000, 4.0, 8.0, "VF", "VF", "VF", "vf_compatible", "valid", False, True, None, {}),
    )
    summary = compute_temporal_summary(segments)
    assert summary[0]["detected"] is True
    assert summary[0]["first_detection_available_seconds"] == 8.0
    assert summary[0]["detection_delay_seconds"] == 8.0
