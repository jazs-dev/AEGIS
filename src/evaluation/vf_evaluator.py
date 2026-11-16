"""Baseline evaluation of the existing deterministic VF classifier."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.algorithms.qrs_detection import detect_qrs
from src.algorithms.vf_detection import classify_ecg
from src.datasets.physionet_loader import PhysioNetRecord, load_record
from src.evaluation.ecg_segmentation import ECGSegment, segment_record
from src.processing.ecg_processing import load_ecg_parameters, process_ecg


@dataclass(frozen=True)
class SegmentEvaluation:
    """Prediction and provenance for one segment."""

    dataset: str
    record_id: str
    start_sample: int
    end_sample: int
    start_seconds: float
    end_seconds: float
    reference_label: str
    reference_rhythm: str
    prediction: str
    detector_category: str
    ecg_quality: str
    abstained: bool
    included_in_binary_metrics: bool
    exclusion_reason: str | None
    features: Mapping[str, float]


@dataclass(frozen=True)
class ConfusionMatrix:
    """Binary confusion counts."""

    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True)
class Metrics:
    """Binary metrics with ``None`` for undefined denominators."""

    confusion: ConfusionMatrix
    sensitivity: float | None
    specificity: float | None
    precision: float | None
    f1: float | None
    accuracy: float | None
    positive_segments: int
    negative_segments: int
    abstentions: int
    evaluated_segments: int


@dataclass(frozen=True)
class EvaluationReport:
    """Complete reproducible report for one evaluation run."""

    metadata: Mapping[str, Any]
    segments: tuple[SegmentEvaluation, ...]
    metrics: Metrics
    metrics_with_vf_abstentions_as_fn: Metrics
    by_dataset: Mapping[str, Metrics]
    by_record: Mapping[str, Metrics]
    by_rhythm: Mapping[str, Metrics]
    by_quality: Mapping[str, Metrics]
    temporal: tuple[Mapping[str, Any], ...]


def evaluate_record(record: PhysioNetRecord, window_seconds: float = 4.0, overlap: float = 0.0) -> tuple[SegmentEvaluation, ...]:
    """Run the unchanged detector on every segment of one loaded record."""
    return tuple(evaluate_segment(segment) for segment in segment_record(record, window_seconds, overlap))


def evaluate_segment(segment: ECGSegment) -> SegmentEvaluation:
    """Process one segment without exposing its reference label to the detector."""
    processed = process_ecg(segment.signal)
    qrs = detect_qrs(processed)
    rhythm = classify_ecg(processed, qrs)
    prediction, abstained = _prediction_from_category(rhythm.rhythm_classification)
    included = segment.reference_label in {"VF", "NON_VF"}
    return SegmentEvaluation(
        segment.dataset,
        segment.record_id,
        segment.start_sample,
        segment.end_sample,
        segment.start_seconds,
        segment.end_seconds,
        segment.reference_label,
        segment.reference_rhythm,
        prediction,
        rhythm.rhythm_classification,
        rhythm.ecg_quality,
        abstained,
        included,
        None if included else segment.label_reason,
        dict(processed.features),
    )


def evaluate_records(records: Iterable[PhysioNetRecord], window_seconds: float = 4.0, overlap: float = 0.0) -> EvaluationReport:
    """Evaluate records and aggregate global, dataset, record, rhythm and quality metrics."""
    record_list = tuple(records)
    all_segments = tuple(item for record in record_list for item in evaluate_record(record, window_seconds, overlap))
    metadata = {
        "datasets": sorted({item.dataset for item in all_segments}),
        "records": sorted({f"{item.dataset}:{item.record_id}" for item in all_segments}),
        "record_metadata": [
            {
                "dataset": record.dataset.key,
                "dataset_version": record.dataset.version,
                "record_id": record.record_id,
                "sampling_rate_hz": record.signal.sampling_rate_hz,
                "amplitude_unit": record.signal.amplitude_unit,
                "channel_index": record.channel_index,
                "channel_name": record.channel_name,
                "record_length_samples": record.record_length_samples,
            }
            for record in record_list
        ],
        "window_seconds": window_seconds,
        "overlap": overlap,
        "detector_parameters_version": load_ecg_parameters().get("version"),
        "detector_parameters_sha256": _parameter_hash(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "real_ecg_metrics": bool(record_list) and all(record.signal.source.startswith("physionet:") for record in record_list),
    }
    return EvaluationReport(
        metadata,
        all_segments,
        compute_metrics(all_segments),
        compute_metrics(all_segments, count_vf_abstentions_as_fn=True),
        _group_metrics(all_segments, lambda item: item.dataset),
        _group_metrics(all_segments, lambda item: f"{item.dataset}:{item.record_id}"),
        _group_metrics(all_segments, lambda item: item.reference_rhythm),
        _group_metrics(all_segments, lambda item: item.ecg_quality),
        compute_temporal_summary(all_segments),
    )


def evaluate_physionet(dataset: str, record_ids: Sequence[str], *, local_root: str | Path | None = None, channel: int = 0, window_seconds: float = 4.0, overlap: float = 0.0) -> EvaluationReport:
    """Load selected records from local WFDB files or PhysioNet and evaluate them."""
    records = tuple(load_record(dataset, record_id, local_root=local_root, channel=channel) for record_id in record_ids)
    return evaluate_records(records, window_seconds, overlap)


def compute_metrics(results: Iterable[SegmentEvaluation], count_vf_abstentions_as_fn: bool = False) -> Metrics:
    """Compute binary metrics on labeled windows, safely handling abstentions."""
    selected = [item for item in results if item.included_in_binary_metrics]
    tp = fp = tn = fn = abstentions = 0
    for item in selected:
        if item.abstained:
            abstentions += 1
            if count_vf_abstentions_as_fn and item.reference_label == "VF":
                fn += 1
            continue
        if item.reference_label == "VF" and item.prediction == "VF":
            tp += 1
        elif item.reference_label == "VF":
            fn += 1
        elif item.prediction == "VF":
            fp += 1
        else:
            tn += 1
    denominator = tp + fp + tn + fn
    return Metrics(
        ConfusionMatrix(tp, fp, tn, fn),
        _ratio(tp, tp + fn),
        _ratio(tn, tn + fp),
        _ratio(tp, tp + fp),
        _ratio(2 * tp, 2 * tp + fp + fn),
        _ratio(tp + tn, denominator),
        sum(item.reference_label == "VF" for item in selected),
        sum(item.reference_label == "NON_VF" for item in selected),
        abstentions,
        denominator,
    )


def save_report(report: EvaluationReport, output_directory: str | Path) -> tuple[Path, Path]:
    """Save JSON metadata/metrics and CSV segment results without ECG binaries."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "evaluation_report.json"
    csv_path = directory / "segment_results.csv"
    payload = {
        "metadata": dict(report.metadata),
        "metrics": _metrics_to_dict(report.metrics),
        "metrics_with_vf_abstentions_as_fn": _metrics_to_dict(report.metrics_with_vf_abstentions_as_fn),
        "by_dataset": {key: _metrics_to_dict(value) for key, value in report.by_dataset.items()},
        "by_record": {key: _metrics_to_dict(value) for key, value in report.by_record.items()},
        "by_rhythm": {key: _metrics_to_dict(value) for key, value in report.by_rhythm.items()},
        "by_quality": {key: _metrics_to_dict(value) for key, value in report.by_quality.items()},
        "temporal": list(report.temporal),
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    fields = list(asdict(report.segments[0]).keys()) if report.segments else ["dataset", "record_id"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for segment in report.segments:
            row = asdict(segment)
            row["features"] = json.dumps(row["features"], sort_keys=True)
            writer.writerow(row)
    return json_path, csv_path


def _prediction_from_category(category: str) -> tuple[str, bool]:
    if category == "vf_compatible":
        return "VF", False
    if category in {"uninterpretable", "not_assessed"}:
        return "ABSTAIN", True
    return "NON_VF", False


def compute_temporal_summary(results: Sequence[SegmentEvaluation]) -> tuple[Mapping[str, Any], ...]:
    """Estimate episode detection delay using segment-end availability times.

    The result is intentionally approximate when source annotations have
    approximate boundaries, as is documented for CUDB.
    """
    summaries: list[Mapping[str, Any]] = []
    grouped: dict[tuple[str, str], list[SegmentEvaluation]] = {}
    for item in results:
        grouped.setdefault((item.dataset, item.record_id), []).append(item)
    for (dataset, record_id), items in grouped.items():
        ordered = sorted(items, key=lambda item: item.start_sample)
        episodes: list[list[SegmentEvaluation]] = []
        for item in ordered:
            if item.reference_label != "VF":
                continue
            if not episodes or item.start_sample != episodes[-1][-1].end_sample:
                episodes.append([])
            episodes[-1].append(item)
        for episode_index, episode in enumerate(episodes, start=1):
            detection = next((item for item in episode if item.prediction == "VF"), None)
            start = episode[0].start_seconds
            summaries.append({
                "dataset": dataset,
                "record_id": record_id,
                "episode_index": episode_index,
                "annotated_start_seconds": start,
                "first_detection_available_seconds": detection.end_seconds if detection else None,
                "detection_delay_seconds": detection.end_seconds - start if detection else None,
                "detected": detection is not None,
                "annotation_boundary_approximate": dataset == "cudb",
            })
        for item in ordered:
            if item.prediction == "VF" and item.reference_label == "NON_VF":
                summaries.append({
                    "dataset": dataset,
                    "record_id": record_id,
                    "episode_index": None,
                    "annotated_start_seconds": None,
                    "first_detection_available_seconds": item.end_seconds,
                    "detection_delay_seconds": None,
                    "detected": False,
                    "false_alarm_outside_vf": True,
                    "segment_start_seconds": item.start_seconds,
                })
    return tuple(summaries)


def _group_metrics(results: Sequence[SegmentEvaluation], key_function: Any) -> dict[str, Metrics]:
    groups: dict[str, list[SegmentEvaluation]] = {}
    for item in results:
        groups.setdefault(str(key_function(item)), []).append(item)
    return {key: compute_metrics(items) for key, items in groups.items()}


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _metrics_to_dict(metrics: Metrics) -> dict[str, Any]:
    payload = asdict(metrics)
    payload["confusion_matrix"] = payload.pop("confusion")
    return payload


def _parameter_hash() -> str:
    from src.processing.config_loader import default_config_directory

    data = (default_config_directory() / "ecg_algorithm_parameters.json").read_bytes()
    return hashlib.sha256(data).hexdigest()
