from __future__ import annotations

from src.integration.monitoring_pipeline import MonitoringPipeline
from src.simulation.physiological_simulator import SimulationConfig


def test_categorical_mode_uses_simulated_categories_and_real_monitor() -> None:
    pipeline = MonitoringPipeline(simulation=SimulationConfig(scenario="SUSPECTED_VF", duration_seconds=2, seed=4), mode="categorical")
    result = pipeline.step()
    assert result is not None
    assert result.ecg_analysis is None
    assert result.modality_label.startswith("Simulación categórica")
    assert result.monitor_result.candidate_state == "SUSPECTED_VF"
    assert result.monitor_result.rule_decision is not None
    assert result.monitor_result.rule_decision.rule_id == "R02"


def test_mathematical_mode_derives_categories_from_the_same_samples() -> None:
    pipeline = MonitoringPipeline(simulation=SimulationConfig(scenario="SUSPECTED_VF", duration_seconds=1, seed=9), mode="mathematical")
    result = pipeline.step()
    assert result is not None and result.ecg_analysis is not None
    analysis = result.ecg_analysis
    assert analysis.signal.source == "synthetic"
    assert result.categories["ecg_quality"] == analysis.rhythm.ecg_quality
    assert result.categories["qrs_status"] == analysis.rhythm.qrs_status
    assert result.categories["rhythm_classification"] == analysis.rhythm.rhythm_classification
    assert result.monitor_result.candidate_state == "SUSPECTED_VF"
    assert result.monitor_result.evaluation_mode == "immediate"


def test_mathematical_arrest_keeps_clinical_evidence_independent_from_ecg() -> None:
    pipeline = MonitoringPipeline(simulation=SimulationConfig(scenario="VF_CARDIAC_ARREST", duration_seconds=1, seed=9), mode="mathematical")
    result = pipeline.step()
    assert result is not None and result.ecg_analysis is not None
    assert result.categories["rhythm_classification"] == "vf_compatible"
    assert result.categories["pulse_status"] == "absent"
    assert result.categories["responsiveness_status"] == "unresponsive"
    assert result.categories["breathing_status"] == "absent"
    assert result.monitor_result.effective_state == "VF_CARDIAC_ARREST"


def test_invalid_math_signal_does_not_invalidate_unrelated_physiology() -> None:
    pipeline = MonitoringPipeline(simulation=SimulationConfig(scenario="SIGNAL_INVALID", duration_seconds=1, seed=9), mode="mathematical")
    result = pipeline.step()
    assert result is not None and result.ecg_analysis is not None
    assert result.categories["ecg_quality"] == "invalid"
    assert result.categories["blood_pressure_status"] == "stable"
    assert result.monitor_result.effective_state == "SIGNAL_INVALID"


def test_session_step_history_and_reset_are_reproducible() -> None:
    pipeline = MonitoringPipeline(simulation=SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=3, interval_seconds=1, seed=2), mode="categorical")
    assert pipeline.step() is not None
    assert len(pipeline.history) == 1
    pipeline.run_all()
    assert len(pipeline.history) == 3
    pipeline.reset()
    assert pipeline.current is None
    assert not pipeline.history
    assert pipeline.step().sample.measurements == MonitoringPipeline(simulation=SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=3, interval_seconds=1, seed=2), mode="categorical").step().sample.measurements


def test_pipeline_result_does_not_use_expected_state_oracle_for_decision() -> None:
    result = MonitoringPipeline(simulation=SimulationConfig(scenario="SUSPECTED_VF", duration_seconds=1, seed=1), mode="categorical").step()
    assert result is not None
    assert result.monitor_result.effective_state == "SUSPECTED_VF"
    assert "expected_state_oracle" not in result.to_dict()
