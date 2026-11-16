from __future__ import annotations

import numpy as np

from src.datasets.physionet_loader import DATASETS, PhysioNetRecord
from src.datasets.rhythm_annotations import parse_annotation_rows
from src.evaluation.ecg_segmentation import label_window, segment_record
from src.processing.ecg_processing import ECGSignal


def make_record() -> PhysioNetRecord:
    signal = ECGSignal(np.ones(2000), 250, "mV", record_id="fixture", source="fixture")
    annotations = parse_annotation_rows(((0, "NSR"), (1000, "VF")), "vfdb")
    return PhysioNetRecord(DATASETS["vfdb"], "fixture", signal, 0, "ECG", "mV", 2000, annotations)


def test_non_overlapping_windows_are_labeled_only_when_fully_covered() -> None:
    segments = segment_record(make_record(), window_seconds=2, overlap=0)
    assert [segment.reference_label for segment in segments] == ["NON_VF", "NON_VF", "VF", "VF"]
    assert segments[2].reference_rhythm == "VF"


def test_transition_window_is_ambiguous_not_forced_into_binary_class() -> None:
    intervals = ((0, 750, "NON_VF", "NSR"), (750, 2000, "VF", "VF"))
    from src.datasets.rhythm_annotations import RhythmInterval

    normalized = tuple(RhythmInterval(*item, "fixture") for item in intervals)
    assert label_window(500, 1000, normalized)[0] == "AMBIGUOUS"
