"""Deterministic segmentation and reference-label policy for ECG records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.datasets.physionet_loader import PhysioNetRecord
from src.datasets.rhythm_annotations import RhythmInterval, build_rhythm_intervals
from src.processing.ecg_processing import ECGSignal


@dataclass(frozen=True)
class ECGSegment:
    """One analysis window and its independently derived reference label."""

    signal: ECGSignal
    dataset: str
    record_id: str
    start_sample: int
    end_sample: int
    reference_label: str
    reference_rhythm: str
    label_reason: str

    @property
    def start_seconds(self) -> float:
        """Return the segment start relative to the record."""
        return self.start_sample / self.signal.sampling_rate_hz

    @property
    def end_seconds(self) -> float:
        """Return the segment end relative to the record."""
        return self.end_sample / self.signal.sampling_rate_hz


def segment_record(record: PhysioNetRecord, window_seconds: float = 4.0, overlap: float = 0.0) -> tuple[ECGSegment, ...]:
    """Segment a record using full windows and a declared overlap fraction.

    A window is positive only when it lies wholly inside one annotated rhythm
    interval.  Windows crossing an annotation boundary are retained as
    ``AMBIGUOUS`` so that they are visible but excluded from binary metrics.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")
    if not 0 <= overlap < 1:
        raise ValueError("overlap must be in the interval [0, 1)")
    width = int(round(window_seconds * record.signal.sampling_rate_hz))
    step = max(1, int(round(width * (1.0 - overlap))))
    intervals = build_rhythm_intervals(record.annotations, record.record_length_samples)
    segments: list[ECGSegment] = []
    for start in range(0, record.record_length_samples - width + 1, step):
        end = start + width
        label, rhythm, reason = label_window(start, end, intervals)
        samples = record.signal.samples[start:end]
        metadata = dict(record.signal.metadata)
        metadata.update({"segment_start_sample": start, "segment_end_sample": end, "reference_label": label, "reference_rhythm": rhythm})
        segment_signal = ECGSignal(samples, record.signal.sampling_rate_hz, record.signal.amplitude_unit, record.signal.start_time, f"{record.record_id}:{start}-{end}", record.signal.source, metadata)
        segments.append(ECGSegment(segment_signal, record.dataset.key, record.record_id, start, end, label, rhythm, reason))
    return tuple(segments)


def label_window(start_sample: int, end_sample: int, intervals: Sequence[RhythmInterval]) -> tuple[str, str, str]:
    """Apply the strict full-window labeling policy."""
    overlaps = [interval for interval in intervals if interval.start_sample < end_sample and interval.end_sample > start_sample]
    if not overlaps:
        return "EXCLUDED", "UNKNOWN", "window has no annotation coverage"
    if len(overlaps) == 1 and overlaps[0].start_sample <= start_sample and overlaps[0].end_sample >= end_sample:
        return overlaps[0].label, overlaps[0].rhythm, "window fully covered by one annotation interval"
    return "AMBIGUOUS", "+".join(sorted({item.rhythm for item in overlaps})), "window intersects an annotation transition"
