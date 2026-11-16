"""Dataset-specific normalization of rhythm-change annotations.

WFDB rhythm annotations describe intervals beginning at an annotation sample;
they are not beat-level truth.  This module preserves the original label and
maps it to an evaluation label without modifying the source annotation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


VF_LABELS = frozenset({"VF", "VFIB"})
KNOWN_NON_VF = frozenset({"VT", "VFL", "AFIB", "NSR", "N", "ASYS", "NOISE", "SBR", "B", "BI", "HGEA", "NOD", "PM", "SVTA", "VER"})


@dataclass(frozen=True)
class RhythmAnnotation:
    """One normalized rhythm-change annotation."""

    sample_index: int
    label: str
    rhythm: str
    source: str


@dataclass(frozen=True)
class RhythmInterval:
    """A half-open interval carrying a normalized reference label."""

    start_sample: int
    end_sample: int
    label: str
    rhythm: str
    reason: str


def normalize_rhythm_label(raw_label: str, dataset: str) -> tuple[str, str]:
    """Map VFDB/CUDB rhythm text to ``VF``, ``NON_VF`` or ``AMBIGUOUS``.

    ``VT`` and ``VFL`` remain distinct in ``rhythm`` even though they are
    negative for the binary VF endpoint.  ``AFIB`` is never mapped to VF.
    """
    del dataset  # The explicit mapping is currently shared by both databases.
    label = str(raw_label or "").strip().upper().replace("(", "").replace(")", "")
    label = label.split()[0] if label else ""
    if label in VF_LABELS:
        return "VF", label
    if label in KNOWN_NON_VF:
        return ("EXCLUDED", label) if label == "NOISE" else ("NON_VF", label)
    return "AMBIGUOUS", label or "UNKNOWN"


def annotations_from_wfdb(annotation: object, dataset: str) -> tuple[RhythmAnnotation, ...]:
    """Convert a WFDB annotation object without passing labels to the detector."""
    samples = getattr(annotation, "sample", ())
    aux_notes = getattr(annotation, "aux_note", ())
    symbols = getattr(annotation, "symbol", ())
    normalized: list[RhythmAnnotation] = []
    for index, sample in enumerate(samples):
        aux = aux_notes[index] if index < len(aux_notes) else ""
        symbol = symbols[index] if index < len(symbols) else ""
        raw = aux.strip() if isinstance(aux, str) and aux.strip() else str(symbol)
        label, rhythm = normalize_rhythm_label(raw, dataset)
        normalized.append(RhythmAnnotation(int(sample), label, rhythm, raw))
    return tuple(normalized)


def build_rhythm_intervals(annotations: Sequence[RhythmAnnotation], record_length_samples: int) -> tuple[RhythmInterval, ...]:
    """Expand rhythm-change annotations into half-open sample intervals."""
    if record_length_samples <= 0:
        raise ValueError("record_length_samples must be positive")
    ordered = sorted((item for item in annotations if 0 <= item.sample_index < record_length_samples), key=lambda item: item.sample_index)
    if not ordered:
        return (RhythmInterval(0, record_length_samples, "AMBIGUOUS", "UNKNOWN", "no rhythm annotation"),)
    intervals: list[RhythmInterval] = []
    if ordered[0].sample_index > 0:
        intervals.append(RhythmInterval(0, ordered[0].sample_index, "AMBIGUOUS", "UNKNOWN", "record begins before first rhythm annotation"))
    for current, following in zip(ordered, (*ordered[1:], None)):
        end = following.sample_index if following else record_length_samples
        intervals.append(RhythmInterval(current.sample_index, end, current.label, current.rhythm, "annotation interval"))
    return tuple(intervals)


def parse_annotation_rows(rows: Iterable[tuple[int, str]], dataset: str) -> tuple[RhythmAnnotation, ...]:
    """Create annotations from small deterministic test fixtures."""
    return tuple(
        RhythmAnnotation(int(sample), normalize_rhythm_label(label, dataset)[0], normalize_rhythm_label(label, dataset)[1], label)
        for sample, label in rows
    )
