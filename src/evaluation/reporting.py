"""Matplotlib reports generated exclusively from evaluation results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.datasets.physionet_loader import PhysioNetRecord
from src.evaluation.ecg_segmentation import segment_record
from src.evaluation.vf_evaluator import EvaluationReport


def write_figures(report: EvaluationReport, output_directory: str | Path, records: tuple[PhysioNetRecord, ...] = (), window_seconds: float = 4.0, overlap: float = 0.0) -> tuple[Path, ...]:
    """Write aggregate figures and, when records are supplied, ECG examples."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = [plot_confusion_matrix(report, directory / "confusion_matrix.png"), plot_prediction_distribution(report, directory / "prediction_distribution.png"), plot_feature_distributions(report, directory / "feature_distributions.png")]
    if records:
        paths.extend(write_example_figures(report, records, directory / "examples", window_seconds, overlap))
    return tuple(paths)


def write_example_figures(report: EvaluationReport, records: tuple[PhysioNetRecord, ...], output_directory: str | Path, window_seconds: float = 4.0, overlap: float = 0.0) -> tuple[Path, ...]:
    """Plot one raw ECG window for each available outcome class."""
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    segments_by_key = {}
    for record in records:
        for segment in segment_record(record, window_seconds=window_seconds, overlap=overlap):
            segments_by_key[(record.dataset.key, record.record_id, segment.start_sample)] = segment
    paths: list[Path] = []
    for outcome in ("tp", "fp", "fn", "tn", "abstain"):
        candidate = next((item for item in report.segments if _outcome(item) == outcome), None)
        if candidate is None:
            continue
        segment = segments_by_key.get((candidate.dataset, candidate.record_id, candidate.start_sample))
        if segment is None:
            continue
        figure, axis = plt.subplots(figsize=(8, 3))
        time = np.arange(segment.signal.samples.size) / segment.signal.sampling_rate_hz
        axis.plot(time, segment.signal.samples, linewidth=0.7)
        axis.set_title(f"{outcome.upper()} · {candidate.dataset}/{candidate.record_id} · ref={candidate.reference_rhythm} · pred={candidate.prediction}")
        axis.set_xlabel("Tiempo (s)")
        axis.set_ylabel(f"ECG ({segment.signal.amplitude_unit})")
        axis.grid(alpha=0.2)
        paths.append(_save(figure, directory / f"{outcome}_{candidate.dataset}_{candidate.record_id}_{candidate.start_sample}.png"))
    return tuple(paths)


def plot_confusion_matrix(report: EvaluationReport, path: str | Path) -> Path:
    """Plot the observed binary confusion counts."""
    matrix = report.metrics.confusion
    values = np.array([[matrix.tn, matrix.fp], [matrix.fn, matrix.tp]])
    fig, axis = plt.subplots(figsize=(4, 3))
    image = axis.imshow(values, cmap="Blues")
    axis.set_xticks([0, 1], ["NON_VF", "VF"])
    axis.set_yticks([0, 1], ["NON_VF", "VF"])
    axis.set_xlabel("Predicción")
    axis.set_ylabel("Referencia")
    axis.set_title("Matriz de confusión")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, str(values[row, column]), ha="center", va="center")
    fig.colorbar(image, ax=axis)
    return _save(fig, path)


def plot_prediction_distribution(report: EvaluationReport, path: str | Path) -> Path:
    """Plot counts of reference and detector labels."""
    labels = ["VF", "NON_VF", "ABSTAIN"]
    reference = [sum(item.reference_label == label for item in report.segments) for label in labels]
    prediction = [sum(item.prediction == label for item in report.segments) for label in labels]
    positions = np.arange(len(labels))
    fig, axis = plt.subplots(figsize=(5, 3))
    axis.bar(positions - 0.2, reference, width=0.4, label="Referencia")
    axis.bar(positions + 0.2, prediction, width=0.4, label="Detector")
    axis.set_xticks(positions, labels)
    axis.set_title("Distribución de etiquetas")
    axis.legend()
    return _save(fig, path)


def plot_feature_distributions(report: EvaluationReport, path: str | Path) -> Path:
    """Plot available VF scores by reference label, if present."""
    labels = ("VF", "NON_VF", "AMBIGUOUS", "EXCLUDED")
    groups = [[item.features.get("vf_score", np.nan) for item in report.segments if item.reference_label == label] for label in labels]
    fig, axis = plt.subplots(figsize=(6, 3))
    axis.boxplot([values if values else [np.nan] for values in groups], tick_labels=labels, showfliers=False)
    axis.set_ylabel("vf_score")
    axis.set_title("Características por etiqueta de referencia")
    return _save(fig, path)


def _save(figure: plt.Figure, path: str | Path) -> Path:
    destination = Path(path)
    figure.tight_layout()
    figure.savefig(destination, dpi=120)
    plt.close(figure)
    return destination


def _outcome(item: object) -> str:
    reference = item.reference_label
    prediction = item.prediction
    if reference == "VF" and prediction == "VF":
        return "tp"
    if reference == "NON_VF" and prediction == "VF":
        return "fp"
    if reference == "VF" and prediction == "NON_VF":
        return "fn"
    if reference == "NON_VF" and prediction == "NON_VF":
        return "tn"
    if item.abstained:
        return "abstain"
    return "other"
