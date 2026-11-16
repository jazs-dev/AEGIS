"""Coordinate simulation, ECG processing and monitoring without Streamlit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping

import numpy as np
from scipy import signal

from src.algorithms.qrs_detection import QRSDetectionResult, detect_qrs
from src.algorithms.vf_detection import VFDetectionResult, classify_ecg
from src.monitoring.monitor import Monitor, MonitorResult
from src.processing.config_loader import Configuration, load_configuration
from src.processing.ecg_processing import ECGProcessed, ECGSignal, process_ecg
from src.processing.variable_classifier import ClassificationResult, classify_measurements
from src.simulation.physiological_simulator import SimulationConfig, SimulationSample, generate_samples


PipelineMode = Literal["categorical", "mathematical"]


@dataclass(frozen=True)
class ECGAnalysis:
    """The exact signal and mathematical outputs used for one decision."""

    signal: ECGSignal
    processed: ECGProcessed
    qrs: QRSDetectionResult | None
    rhythm: VFDetectionResult | None


@dataclass(frozen=True)
class PipelineResult:
    """Traceable output of one pipeline sample."""

    sample: SimulationSample
    mode: PipelineMode
    physiological_results: Mapping[str, ClassificationResult]
    categories: Mapping[str, str]
    monitor_result: MonitorResult
    ecg_analysis: ECGAnalysis | None

    @property
    def modality_label(self) -> str:
        """Return the user-facing modality description."""
        return (
            "Simulación categórica — sin detección matemática ECG"
            if self.mode == "categorical"
            else "Análisis ECG experimental — clasificación calculada"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable result without exposing oracle decisions."""
        return {
            "timestamp": self.sample.timestamp.isoformat(),
            "mode": self.mode,
            "scenario_reference": self.sample.scenario,
            "physiological_results": {key: value.to_dict() for key, value in self.physiological_results.items()},
            "categories": dict(self.categories),
            "monitor_result": self.monitor_result.to_dict(),
            "ecg_analysis": None if self.ecg_analysis is None else {
                "record_id": self.ecg_analysis.signal.record_id,
                "sampling_rate_hz": self.ecg_analysis.signal.sampling_rate_hz,
                "amplitude_unit": self.ecg_analysis.signal.amplitude_unit,
                "source": self.ecg_analysis.signal.source,
                "qrs_positions": list(self.ecg_analysis.qrs.positions) if self.ecg_analysis.qrs else [],
                "features": dict(self.ecg_analysis.processed.features),
            },
        }


class MonitoringPipeline:
    """Stateful, reproducible adapter consumed by Streamlit or tests."""

    def __init__(
        self,
        configuration: Configuration | None = None,
        simulation: SimulationConfig | None = None,
        mode: PipelineMode = "categorical",
    ) -> None:
        if mode not in {"categorical", "mathematical"}:
            raise ValueError(f"Unknown pipeline mode: {mode}")
        self.configuration = configuration or load_configuration()
        self.simulation = simulation or SimulationConfig()
        self.mode = mode
        self._samples = generate_samples(self.simulation)
        self._monitor = Monitor(self.configuration)
        self._index = 0
        self._history: list[PipelineResult] = []

    @property
    def completed(self) -> bool:
        """Whether all generated samples have been processed."""
        return self._index >= len(self._samples)

    @property
    def history(self) -> tuple[PipelineResult, ...]:
        """Return processed pipeline results in temporal order."""
        return tuple(self._history)

    @property
    def current(self) -> PipelineResult | None:
        """Return the latest result, if a sample has been processed."""
        return self._history[-1] if self._history else None

    def reset(self) -> None:
        """Reset samples, monitor state and history to the initial state."""
        self._samples = generate_samples(self.simulation)
        self._monitor = Monitor(self.configuration)
        self._index = 0
        self._history.clear()

    def step(self) -> PipelineResult | None:
        """Process one sample without sleeping or using the scenario oracle."""
        if self.completed:
            return None
        sample = self._samples[self._index]
        physiological = classify_measurements(sample.measurements, sample.units, self.configuration)
        categories = {name: result.status for name, result in physiological.items()}
        ecg_analysis = None
        if self.mode == "categorical":
            categories.update(sample.ecg_categories)
        else:
            ecg_signal = generate_synthetic_ecg(sample.scenario, self.simulation.seed, self._index, sample.timestamp)
            processed = process_ecg(ecg_signal)
            qrs = detect_qrs(processed)
            rhythm = classify_ecg(processed, qrs)
            ecg_analysis = ECGAnalysis(ecg_signal, processed, qrs, rhythm)
            categories.update(rhythm.categories())
        categories.update(sample.clinical_evidence)
        monitor_result = self._monitor.evaluate(categories, timestamp=sample.timestamp, external_controls=sample.external_controls)
        result = PipelineResult(sample, self.mode, physiological, categories, monitor_result, ecg_analysis)
        self._history.append(result)
        self._index += 1
        return result

    def run_all(self) -> tuple[PipelineResult, ...]:
        """Process every remaining sample deterministically."""
        while not self.completed:
            self.step()
        return self.history


def generate_synthetic_ecg(scenario: str, seed: int, sample_index: int, timestamp: datetime) -> ECGSignal:
    """Generate a labelled synthetic waveform for mathematical demonstration.

    The scenario selects waveform morphology only; it is never passed to the
    classifier or monitor as a state decision.  The returned samples are the
    exact samples later processed and displayed by the dashboard.
    """
    sampling_rate = 250.0
    seconds = 8.0
    count = int(sampling_rate * seconds)
    time = np.arange(count) / sampling_rate
    rng = np.random.default_rng(seed + sample_index * 1009)
    if scenario in {"SUSPECTED_VF", "VF_CARDIAC_ARREST"}:
        raw = rng.normal(size=count)
        sos = signal.butter(4, [3.0, 12.0], btype="bandpass", fs=sampling_rate, output="sos")
        samples = signal.sosfiltfilt(sos, raw)
        samples = samples / (np.std(samples) or 1.0) * 0.1
    elif scenario == "SIGNAL_INVALID":
        samples = np.zeros(count)
    else:
        samples = np.zeros(count)
        if scenario == "ABNORMAL_RHYTHM":
            beats = (0.45, 1.12, 1.84, 2.98, 3.44, 4.70, 5.31, 6.65, 7.18)
        else:
            beats = tuple(np.arange(0.5, seconds, 1.0))
        for beat in beats:
            samples += 1.2 * np.exp(-((time - beat) / 0.025) ** 2)
            samples -= 0.2 * np.exp(-((time - beat - 0.08) / 0.04) ** 2)
        samples += rng.normal(0.0, 0.002, count)
    return ECGSignal(samples, sampling_rate, "mV", timestamp, f"synthetic-{seed}-{sample_index}", "synthetic", {"simulated": True, "scenario_reference": scenario})
