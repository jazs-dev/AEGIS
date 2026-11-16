"""Reproducible physiological simulation connected to the decision monitor.

The ECG and clinical categories generated here are explicit simulation inputs.
They are not produced by an ECG detector and must not be interpreted as a
clinical diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import math
import random
from typing import Any, Mapping, Sequence

from src.monitoring.monitor import Monitor, MonitorResult
from src.processing.config_loader import Configuration, load_configuration
from src.processing.variable_classifier import ClassificationResult, classify_measurements


SCENARIOS = {
    "NORMAL_MONITORING",
    "ABNORMAL_RHYTHM",
    "SUSPECTED_VF",
    "VF_CARDIAC_ARREST",
    "SIGNAL_INVALID",
}
DEFAULT_START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
EXPECTED_STATES = {scenario: scenario for scenario in SCENARIOS}


@dataclass(frozen=True)
class ScenarioSegment:
    """One named scenario segment in a reproducible sequence."""

    scenario: str
    duration_seconds: float
    external_controls: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"Unknown simulation scenario: {self.scenario}")
        if not math.isfinite(self.duration_seconds) or self.duration_seconds <= 0:
            raise ValueError("Scenario duration_seconds must be finite and greater than zero")


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration for one scenario or a sequence of scenario segments."""

    scenario: str = "NORMAL_MONITORING"
    duration_seconds: float = 10.0
    interval_seconds: float = 1.0
    seed: int = 0
    start_time: datetime = DEFAULT_START_TIME
    scenario_segments: tuple[ScenarioSegment, ...] = ()

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError(f"Unknown simulation scenario: {self.scenario}")
        if not math.isfinite(self.duration_seconds) or self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be finite and greater than zero")
        if not math.isfinite(self.interval_seconds) or self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be finite and greater than zero")
        if self.start_time.tzinfo is None:
            raise ValueError("start_time must be timezone-aware")
        if self.scenario_segments and not all(isinstance(segment, ScenarioSegment) for segment in self.scenario_segments):
            raise ValueError("scenario_segments must contain ScenarioSegment values")


@dataclass(frozen=True)
class SimulationSample:
    """Raw synthetic sample before physiological classification."""

    timestamp: datetime
    scenario: str
    measurements: Mapping[str, Any]
    units: Mapping[str, str]
    ecg_categories: Mapping[str, str]
    clinical_evidence: Mapping[str, str]
    metadata: Mapping[str, Any]
    external_controls: Mapping[str, Any] = field(default_factory=dict)

    @property
    def expected_state(self) -> str:
        """Return the scenario label used only as an external test oracle."""
        return EXPECTED_STATES[self.scenario]

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable raw sample payload."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "scenario": self.scenario,
            "measurements": dict(self.measurements),
            "units": dict(self.units),
            "ecg_categories": dict(self.ecg_categories),
            "clinical_evidence": dict(self.clinical_evidence),
            "metadata": dict(self.metadata),
            "external_controls": dict(self.external_controls),
        }


@dataclass(frozen=True)
class SimulationResult:
    """Processed sample plus the monitor result generated from it."""

    sample: SimulationSample
    physiological_results: Mapping[str, ClassificationResult]
    categories: Mapping[str, str]
    monitor_result: MonitorResult

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable processed sample payload."""
        return {
            "sample": self.sample.to_dict(),
            "physiological_results": {name: result.to_dict() for name, result in self.physiological_results.items()},
            "categories": dict(self.categories),
            "monitor_result": self.monitor_result.to_dict(),
        }


def generate_samples(configuration: SimulationConfig) -> tuple[SimulationSample, ...]:
    """Generate raw samples for one scenario or the configured sequence."""
    rng = random.Random(configuration.seed)
    if configuration.scenario_segments:
        return _generate_sequence(configuration, rng)
    return _generate_segment(
        configuration.scenario,
        configuration.duration_seconds,
        configuration.interval_seconds,
        configuration.start_time,
        rng,
        configuration.seed,
        0,
    )


def run_simulation(
    configuration: SimulationConfig,
    monitor: Monitor | None = None,
    loaded_configuration: Configuration | None = None,
) -> tuple[SimulationResult, ...]:
    """Generate samples and feed them through the existing processing stack.

    The scenario label is retained as metadata only.  The effective state is
    always calculated by the physiological classifier, rule engine, and state
    machine.
    """
    config = loaded_configuration or load_configuration()
    active_monitor = monitor or Monitor(config)
    results: list[SimulationResult] = []
    for sample in generate_samples(configuration):
        physiological_results = classify_measurements(sample.measurements, sample.units, config)
        categories = {name: result.status for name, result in physiological_results.items()}
        categories.update(sample.ecg_categories)
        categories.update(sample.clinical_evidence)
        monitor_result = active_monitor.evaluate(
            categories,
            timestamp=sample.timestamp,
            external_controls=sample.external_controls,
        )
        results.append(SimulationResult(sample, physiological_results, categories, monitor_result))
    return tuple(results)


def _generate_sequence(configuration: SimulationConfig, rng: random.Random) -> tuple[SimulationSample, ...]:
    samples: list[SimulationSample] = []
    timestamp = configuration.start_time
    for segment_index, segment in enumerate(configuration.scenario_segments):
        segment_samples = _generate_segment(
            segment.scenario,
            segment.duration_seconds,
            configuration.interval_seconds,
            timestamp,
            rng,
            configuration.seed,
            segment_index,
        )
        if segment.external_controls:
            segment_samples = tuple(
                _with_external_controls(sample, segment.external_controls) for sample in segment_samples
            )
        samples.extend(segment_samples)
        timestamp += timedelta(seconds=segment.duration_seconds)
    return tuple(samples)


def _generate_segment(
    scenario: str,
    duration_seconds: float,
    interval_seconds: float,
    start_time: datetime,
    rng: random.Random,
    seed: int,
    segment_index: int,
) -> tuple[SimulationSample, ...]:
    count = max(1, math.ceil(duration_seconds / interval_seconds))
    return tuple(
        _build_sample(scenario, start_time + timedelta(seconds=index * interval_seconds), rng, seed, segment_index, index)
        for index in range(count)
    )


def _build_sample(
    scenario: str,
    timestamp: datetime,
    rng: random.Random,
    seed: int,
    segment_index: int,
    sample_index: int,
) -> SimulationSample:
    measurements: dict[str, Any]
    ecg_categories: dict[str, str]
    clinical_evidence: dict[str, str]

    if scenario == "NORMAL_MONITORING":
        measurements = {
            "heart_rate": 72.0 + rng.uniform(-2.0, 2.0),
            "spo2": 98.0 + rng.uniform(-0.4, 0.4),
            "respiratory_rate": 16.0 + rng.uniform(-1.0, 1.0),
            "systolic_pressure": 110.0 + rng.uniform(-3.0, 3.0),
            "diastolic_pressure": 70.0 + rng.uniform(-2.0, 2.0),
            "body_temperature": 36.8 + rng.uniform(-0.15, 0.15),
        }
        ecg_categories = {"ecg_quality": "valid", "qrs_status": "organized", "rhythm_classification": "normal_sinus"}
        clinical_evidence = {"pulse_status": "present", "responsiveness_status": "responsive", "breathing_status": "normal"}
    elif scenario == "ABNORMAL_RHYTHM":
        variant = rng.choice(("tachycardia", "bradycardia"))
        heart_rate = 116.0 + rng.uniform(-3.0, 3.0) if variant == "tachycardia" else 52.0 + rng.uniform(-2.0, 2.0)
        measurements = {
            "heart_rate": heart_rate,
            "spo2": 97.0 + rng.uniform(-0.4, 0.4),
            "respiratory_rate": 17.0 + rng.uniform(-1.0, 1.0),
            "systolic_pressure": 108.0 + rng.uniform(-3.0, 3.0),
            "diastolic_pressure": 70.0 + rng.uniform(-2.0, 2.0),
            "body_temperature": 36.8 + rng.uniform(-0.15, 0.15),
        }
        ecg_categories = {"ecg_quality": "valid", "qrs_status": "abnormal", "rhythm_classification": "abnormal_non_vf"}
        clinical_evidence = {"pulse_status": "present", "responsiveness_status": "responsive", "breathing_status": "normal"}
    elif scenario == "SUSPECTED_VF":
        measurements = {
            "heart_rate": None,
            "spo2": None,
            "respiratory_rate": None,
            "systolic_pressure": None,
            "diastolic_pressure": None,
            "body_temperature": None,
        }
        ecg_categories = {"ecg_quality": "valid", "qrs_status": "not_organized", "rhythm_classification": "vf_compatible"}
        clinical_evidence = {"pulse_status": "not_assessed", "responsiveness_status": "not_assessed", "breathing_status": "not_assessed"}
    elif scenario == "VF_CARDIAC_ARREST":
        measurements = {
            "heart_rate": None,
            "spo2": None,
            "respiratory_rate": None,
            "systolic_pressure": None,
            "diastolic_pressure": None,
            "body_temperature": None,
        }
        ecg_categories = {"ecg_quality": "valid", "qrs_status": "not_organized", "rhythm_classification": "vf_compatible"}
        clinical_evidence = {"pulse_status": "absent", "responsiveness_status": "unresponsive", "breathing_status": "absent"}
    else:
        measurements = {
            "heart_rate": None,
            "spo2": 101.0,
            "respiratory_rate": None,
            "systolic_pressure": 110.0,
            "diastolic_pressure": 70.0,
            "body_temperature": None,
        }
        ecg_categories = {"ecg_quality": "invalid", "qrs_status": "uninterpretable", "rhythm_classification": "uninterpretable"}
        clinical_evidence = {"pulse_status": "not_assessed", "responsiveness_status": "not_assessed", "breathing_status": "not_assessed"}

    units = {
        "heart_rate": "bpm",
        "spo2": "%",
        "respiratory_rate": "breaths_per_minute",
        "systolic_pressure": "mmHg",
        "diastolic_pressure": "mmHg",
    }
    metadata = {
        "source": "physiological_simulator",
        "simulated": True,
        "scenario": scenario,
        "expected_state_oracle": EXPECTED_STATES[scenario],
        "seed": seed,
        "segment_index": segment_index,
        "sample_index": sample_index,
        "ecg_categories_simulated": True,
        "clinical_evidence_simulated": True,
    }
    return SimulationSample(timestamp, scenario, measurements, units, ecg_categories, clinical_evidence, metadata)


def _with_external_controls(sample: SimulationSample, controls: Mapping[str, Any]) -> SimulationSample:
    metadata = dict(sample.metadata)
    metadata["external_controls_supplied"] = True
    # Controls are carried explicitly; the simulator never generates them.
    metadata["external_controls"] = dict(controls)
    return SimulationSample(sample.timestamp, sample.scenario, sample.measurements, sample.units, sample.ecg_categories, sample.clinical_evidence, metadata, dict(controls))
