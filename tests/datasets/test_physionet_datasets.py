from __future__ import annotations

import numpy as np
import wfdb

from src.datasets.physionet_loader import load_record
from src.datasets.rhythm_annotations import build_rhythm_intervals, normalize_rhythm_label, parse_annotation_rows


def test_reference_mapping_keeps_vt_flutter_and_afib_outside_vf() -> None:
    assert normalize_rhythm_label("VFIB", "vfdb")[0] == "VF"
    assert normalize_rhythm_label("VT", "vfdb") == ("NON_VF", "VT")
    assert normalize_rhythm_label("VFL", "vfdb") == ("NON_VF", "VFL")
    assert normalize_rhythm_label("AFIB", "vfdb") == ("NON_VF", "AFIB")
    assert normalize_rhythm_label("NOISE", "vfdb")[0] == "EXCLUDED"


def test_annotation_intervals_and_transition_policy() -> None:
    annotations = parse_annotation_rows(((0, "NSR"), (1000, "VF")), "vfdb")
    intervals = build_rhythm_intervals(annotations, 2000)
    assert [(item.start_sample, item.end_sample, item.label) for item in intervals] == [(0, 1000, "NON_VF"), (1000, 2000, "VF")]


def test_local_wfdb_record_and_annotation_are_loaded_without_modifying_samples(tmp_path) -> None:
    samples = np.sin(np.arange(1000) / 250 * 2 * np.pi).reshape(-1, 1)
    wfdb.wrsamp("fixture", write_dir=str(tmp_path), fs=250, units=["mV"], sig_name=["ECG"], p_signal=samples)
    wfdb.wrann("fixture", "atr", write_dir=str(tmp_path), sample=np.array([0]), symbol=["+"], aux_note=["(VF"])
    loaded = load_record("vfdb", "fixture", local_root=tmp_path)
    np.testing.assert_allclose(loaded.signal.samples, samples[:, 0], atol=1e-5)
    assert loaded.signal.sampling_rate_hz == 250
    assert loaded.units == "mV"
    assert loaded.annotations[0].label == "VF"
    assert loaded.annotations[0].rhythm == "VF"
