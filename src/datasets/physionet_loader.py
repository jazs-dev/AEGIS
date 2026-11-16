"""Lazy WFDB loader for local PhysioNet files or remote PhysioNet records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from src.datasets.rhythm_annotations import RhythmAnnotation, annotations_from_wfdb
from src.processing.ecg_processing import ECGSignal


class PhysioNetLoaderError(RuntimeError):
    """Raised when a WFDB record or annotation cannot be loaded."""


@dataclass(frozen=True)
class DatasetSpec:
    """Official dataset identifiers used by the loader."""

    key: str
    version: str
    physionet_directory: str
    description: str


DATASETS = {
    "cudb": DatasetSpec("cudb", "1.0.0", "cudb/1.0.0", "CU Ventricular Tachyarrhythmia Database"),
    "vfdb": DatasetSpec("vfdb", "1.0.0", "vfdb/1.0.0", "MIT-BIH Malignant Ventricular Ectopy Database"),
}


@dataclass(frozen=True)
class PhysioNetRecord:
    """Loaded ECG segment plus source metadata and normalized annotations."""

    dataset: DatasetSpec
    record_id: str
    signal: ECGSignal
    channel_index: int
    channel_name: str
    units: str
    record_length_samples: int
    annotations: tuple[RhythmAnnotation, ...]


def get_dataset_spec(dataset: str) -> DatasetSpec:
    """Return a supported dataset specification."""
    try:
        return DATASETS[dataset.lower()]
    except KeyError as exc:
        raise PhysioNetLoaderError(f"Unsupported PhysioNet dataset: {dataset}") from exc


def list_record_ids(dataset: str, local_root: str | Path | None = None) -> tuple[str, ...]:
    """List local WFDB records or query the remote PhysioNet record index."""
    spec = get_dataset_spec(dataset)
    if local_root is not None:
        root = Path(local_root)
        candidates = list(root.glob("*.hea")) + list((root / spec.key).glob("*.hea"))
        return tuple(sorted({path.stem for path in candidates}))
    wfdb = _wfdb()
    try:
        return tuple(sorted(wfdb.get_record_list(spec.key)))
    except Exception as exc:  # library raises several network-specific exceptions
        raise PhysioNetLoaderError(f"Unable to list remote records for {spec.key}: {exc}") from exc


def load_record(
    dataset: str,
    record_id: str,
    *,
    local_root: str | Path | None = None,
    channel: int = 0,
    annotator: str = "atr",
    sampfrom: int = 0,
    sampto: int | None = None,
) -> PhysioNetRecord:
    """Load one channel and its rhythm-change annotations through WFDB."""
    spec = get_dataset_spec(dataset)
    wfdb = _wfdb()
    path, pn_dir = _record_location(spec, record_id, local_root)
    try:
        kwargs: dict[str, Any] = {"physical": True, "channel_names": None, "sampfrom": sampfrom}
        if sampto is not None:
            kwargs["sampto"] = sampto
        record = wfdb.rdrecord(path, pn_dir=pn_dir, **kwargs) if pn_dir else wfdb.rdrecord(path, **kwargs)
        if record.p_signal is None or record.p_signal.ndim != 2:
            raise PhysioNetLoaderError(f"Record {record_id} does not contain physical ECG samples")
        if channel < 0 or channel >= record.p_signal.shape[1]:
            raise PhysioNetLoaderError(f"Channel {channel} is unavailable in {record_id}")
        units = str(record.units[channel])
        if units not in {"mV", "V"}:
            raise PhysioNetLoaderError(f"Unsupported ECG amplitude unit {units!r} in {record_id}")
        annotation = wfdb.rdann(path, annotator, pn_dir=pn_dir) if pn_dir else wfdb.rdann(path, annotator)
    except PhysioNetLoaderError:
        raise
    except Exception as exc:
        raise PhysioNetLoaderError(f"Unable to load {spec.key}/{record_id}: {exc}") from exc
    annotations = annotations_from_wfdb(annotation, spec.key)
    metadata = {
        "dataset": spec.key,
        "dataset_version": spec.version,
        "record_length_samples": int(record.sig_len),
        "channel_index": channel,
        "channel_name": str(record.sig_name[channel]),
        "wfdb_annotator": annotator,
        "source_url": f"https://physionet.org/content/{spec.key}/{spec.version}/",
    }
    signal = ECGSignal(record.p_signal[:, channel], float(record.fs), units, None, record_id, f"physionet:{spec.key}", metadata)
    return PhysioNetRecord(spec, record_id, signal, channel, str(record.sig_name[channel]), units, int(record.sig_len), annotations)


def _record_location(spec: DatasetSpec, record_id: str, local_root: str | Path | None) -> tuple[str, str | None]:
    if local_root is None:
        return record_id, spec.physionet_directory
    root = Path(local_root)
    candidates = (root / record_id, root / spec.key / record_id)
    for candidate in candidates:
        if candidate.with_suffix(".hea").is_file():
            return str(candidate), None
    raise PhysioNetLoaderError(f"Local WFDB header not found for {record_id} under {root}")


def _wfdb() -> Any:
    try:
        import wfdb
    except ImportError as exc:
        raise PhysioNetLoaderError("wfdb is required; install the pinned project dependencies") from exc
    return wfdb
