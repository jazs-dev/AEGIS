from __future__ import annotations

import numpy as np
import pytest

from src.processing.ecg_processing import ECGProcessingError, ECGSignal, filter_ecg, process_ecg, segment_ecg, validate_ecg_signal


def ecg(samples: np.ndarray, **metadata) -> ECGSignal:
    return ECGSignal(samples, 250.0, "mV", "2026-01-01T00:00:00+00:00", "test", "synthetic", metadata)


def test_signal_contract_and_processing_preserve_raw_samples() -> None:
    samples = np.sin(np.arange(1000) / 250 * 2 * np.pi)
    result = process_ecg(ecg(samples))
    assert result.ecg_quality == "valid"
    np.testing.assert_array_equal(result.raw_samples, samples)
    assert {"rms", "energy", "vf_band_power_ratio", "spectral_entropy"} <= set(result.features)


def test_missing_values_are_tracked_without_mutating_raw_input() -> None:
    samples = np.sin(np.arange(1000) / 250 * 2 * np.pi)
    samples[100] = np.nan
    result = process_ecg(ecg(samples))
    assert result.validation.missing_samples_ratio == pytest.approx(0.001)
    assert np.isnan(result.raw_samples[100])


def test_volt_input_is_normalized_for_processing_but_raw_unit_is_preserved() -> None:
    millivolts = np.sin(np.arange(1000) / 250 * 2 * np.pi) * 0.1
    result = process_ecg(ECGSignal(millivolts / 1000, 250.0, "V"))
    assert result.ecg_quality == "valid"
    np.testing.assert_array_equal(result.raw_samples, millivolts / 1000)


@pytest.mark.parametrize("samples", [np.zeros(1000), np.full(1000, 0.01)])
def test_constant_or_low_information_signal_is_invalid(samples: np.ndarray) -> None:
    assert validate_ecg_signal(ecg(samples)).valid is False


def test_short_signal_is_invalid_and_filter_is_not_attempted() -> None:
    short = ecg(np.ones(100))
    assert validate_ecg_signal(short).status == "invalid"
    with pytest.raises(ECGProcessingError):
        filter_ecg(short)


def test_saturation_is_reported_when_adc_limits_are_known() -> None:
    samples = np.sin(np.arange(1000) / 250 * 2 * np.pi)
    samples[:100] = 1.0
    validation = validate_ecg_signal(ecg(samples, adc_min=-1.0, adc_max=1.0))
    assert validation.clipping_ratio >= 0.1
    assert validation.valid is False


def test_segmentation_is_deterministic() -> None:
    signal = ecg(np.arange(2000, dtype=float))
    windows = segment_ecg(signal, 4.0, 2.0)
    assert len(windows) == 3
    assert windows[0].samples.size == 1000
    assert windows[1].record_id.endswith(":500")
