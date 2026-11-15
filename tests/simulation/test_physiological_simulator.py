from datetime import datetime, timezone

import pytest

from src.simulation.physiological_simulator import (
    SCENARIOS,
    ScenarioSegment,
    SimulationConfig,
    generate_samples,
    run_simulation,
)


START = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_each_scenario_generates_expected_effective_state(scenario):
    results = run_simulation(SimulationConfig(scenario=scenario, duration_seconds=2, seed=7, start_time=START))
    assert results
    assert all(result.sample.scenario == scenario for result in results)
    assert all(result.sample.metadata["simulated"] for result in results)
    assert results[-1].monitor_result.effective_state == scenario


def test_fixed_seed_is_reproducible():
    configuration = SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=4, seed=123, start_time=START)
    first = generate_samples(configuration)
    second = generate_samples(configuration)
    assert first == second


def test_different_seeds_change_measurements_without_changing_scenario_category():
    first = run_simulation(SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=4, seed=1, start_time=START))
    second = run_simulation(SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=4, seed=2, start_time=START))
    assert any(a.sample.measurements != b.sample.measurements for a, b in zip(first, second))
    assert {result.monitor_result.effective_state for result in first} == {"NORMAL_MONITORING"}
    assert {result.monitor_result.effective_state for result in second} == {"NORMAL_MONITORING"}


def test_normal_scenario_uses_existing_physiological_classifier():
    result = run_simulation(SimulationConfig(scenario="NORMAL_MONITORING", duration_seconds=1, seed=4, start_time=START))[0]
    assert result.physiological_results["heart_rate_status"].status == "normal_for_context"
    assert result.physiological_results["spo2_status"].status == "adequate"
    assert result.physiological_results["respiratory_rate_status"].status == "normal_for_context"
    assert result.physiological_results["blood_pressure_status"].status == "stable"
    assert result.categories["rhythm_classification"] == "normal_sinus"


def test_abnormal_scenario_can_generate_tachycardia_or_bradycardia_without_vf():
    results = run_simulation(SimulationConfig(scenario="ABNORMAL_RHYTHM", duration_seconds=8, seed=5, start_time=START))
    heart_rate_categories = {result.physiological_results["heart_rate_status"].status for result in results}
    assert heart_rate_categories <= {"tachycardia", "bradycardia"}
    assert all(result.categories["rhythm_classification"] == "abnormal_non_vf" for result in results)
    assert all(result.monitor_result.effective_state == "ABNORMAL_RHYTHM" for result in results)


def test_suspected_vf_works_without_complementary_measurements():
    result = run_simulation(SimulationConfig(scenario="SUSPECTED_VF", duration_seconds=1, seed=5, start_time=START))[0]
    assert result.sample.measurements["spo2"] is None
    assert result.sample.measurements["systolic_pressure"] is None
    assert result.categories["ecg_quality"] == "valid"
    assert result.categories["rhythm_classification"] == "vf_compatible"
    assert result.monitor_result.candidate_state == "SUSPECTED_VF"
    assert result.monitor_result.evaluation_mode == "immediate"


def test_arrest_requires_explicit_simulated_clinical_evidence():
    result = run_simulation(SimulationConfig(scenario="VF_CARDIAC_ARREST", duration_seconds=1, seed=5, start_time=START))[0]
    assert result.sample.clinical_evidence == {
        "pulse_status": "absent",
        "responsiveness_status": "unresponsive",
        "breathing_status": "absent",
    }
    assert result.sample.metadata["clinical_evidence_simulated"]
    assert result.monitor_result.effective_state == "VF_CARDIAC_ARREST"


def test_signal_invalid_preserves_independent_physiological_validity_categories():
    result = run_simulation(SimulationConfig(scenario="SIGNAL_INVALID", duration_seconds=1, seed=5, start_time=START))[0]
    assert result.categories["ecg_quality"] == "invalid"
    assert result.categories["heart_rate_status"] == "not_assessed"
    assert result.categories["spo2_status"] == "invalid"
    assert result.categories["blood_pressure_status"] == "stable"
    assert result.monitor_result.effective_state == "SIGNAL_INVALID"


def test_sequence_reaches_abnormal_suspected_and_arrest_using_configured_transitions():
    configuration = SimulationConfig(
        interval_seconds=1,
        seed=8,
        start_time=START,
        scenario_segments=(
            ScenarioSegment("SIGNAL_INVALID", 5),
            ScenarioSegment("ABNORMAL_RHYTHM", 5),
            ScenarioSegment("SUSPECTED_VF", 1),
            ScenarioSegment("VF_CARDIAC_ARREST", 1),
        ),
    )
    results = run_simulation(configuration)
    first_result_by_scenario = {}
    for result in results:
        first_result_by_scenario.setdefault(result.sample.scenario, result.monitor_result)
    assert [first_result_by_scenario[scenario].effective_state for scenario in (
        "SIGNAL_INVALID", "ABNORMAL_RHYTHM", "SUSPECTED_VF", "VF_CARDIAC_ARREST"
    )] == ["SIGNAL_INVALID", "ABNORMAL_RHYTHM", "SUSPECTED_VF", "VF_CARDIAC_ARREST"]
    assert results[-1].monitor_result.evaluation_mode == "immediate"


def test_normal_to_abnormal_attempt_is_rejected_by_current_configuration():
    configuration = SimulationConfig(
        interval_seconds=1,
        seed=8,
        start_time=START,
        scenario_segments=(ScenarioSegment("NORMAL_MONITORING", 5), ScenarioSegment("ABNORMAL_RHYTHM", 1)),
    )
    results = run_simulation(configuration)
    assert results[0].monitor_result.effective_state == "NORMAL_MONITORING"
    abnormal_result = results[-1].monitor_result
    assert abnormal_result.candidate_state == "ABNORMAL_RHYTHM"
    assert abnormal_result.effective_state == "NORMAL_MONITORING"
    assert abnormal_result.transition is not None
    assert not abnormal_result.transition.allowed


def test_arrest_is_retained_without_automatically_generated_authorization():
    configuration = SimulationConfig(
        interval_seconds=1,
        seed=8,
        start_time=START,
        scenario_segments=(ScenarioSegment("VF_CARDIAC_ARREST", 1), ScenarioSegment("NORMAL_MONITORING", 1)),
    )
    results = run_simulation(configuration)
    assert results[0].monitor_result.effective_state == "VF_CARDIAC_ARREST"
    assert results[1].monitor_result.candidate_state == "NORMAL_MONITORING"
    assert results[1].monitor_result.effective_state == "VF_CARDIAC_ARREST"
    assert not results[1].monitor_result.transition.allowed


def test_explicit_external_controls_can_exit_arrest():
    configuration = SimulationConfig(
        interval_seconds=1,
        seed=8,
        start_time=START,
        scenario_segments=(
            ScenarioSegment("VF_CARDIAC_ARREST", 1),
            ScenarioSegment(
                "NORMAL_MONITORING",
                1,
                external_controls={
                    "authorized_clinical_operator": True,
                    "post_event_circulation_assessment": "completed",
                },
            ),
        ),
    )
    results = run_simulation(configuration)
    assert results[-1].monitor_result.effective_state == "NORMAL_MONITORING"
    assert results[-1].monitor_result.transition.transition_id == "T10"


def test_simulation_result_preserves_raw_categories_and_monitor_trace():
    result = run_simulation(SimulationConfig(scenario="SUSPECTED_VF", duration_seconds=1, seed=1, start_time=START))[0]
    payload = result.to_dict()
    assert payload["sample"]["metadata"]["source"] == "physiological_simulator"
    assert payload["categories"]["qrs_status"] == "not_organized"
    assert payload["monitor_result"]["rule_decision"]["rule_id"] == "R02"
    assert payload["monitor_result"]["transition"]["transition_id"] == "T02"


def test_invalid_simulation_parameters_are_rejected():
    with pytest.raises(ValueError):
        SimulationConfig(duration_seconds=0)
    with pytest.raises(ValueError):
        SimulationConfig(interval_seconds=0)
    with pytest.raises(ValueError):
        SimulationConfig(scenario="UNKNOWN")
    with pytest.raises(ValueError):
        ScenarioSegment("NORMAL_MONITORING", 0)
