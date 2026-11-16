from datetime import datetime, timezone

import pytest

from src.monitoring.monitor import Monitor
from src.monitoring.rule_engine import RuleInputError, evaluate_rules
from src.monitoring.state_machine import StateMachine


NORMAL = {
    "heart_rate_status": "normal_for_context",
    "spo2_status": "adequate",
    "respiratory_rate_status": "normal_for_context",
    "blood_pressure_status": "stable",
    "ecg_quality": "valid",
    "rhythm_classification": "normal_sinus",
    "qrs_status": "organized",
    "pulse_status": "present",
    "responsiveness_status": "responsive",
    "breathing_status": "normal",
}

ABNORMAL = {
    **NORMAL,
    "heart_rate_status": "tachycardia",
    "rhythm_classification": "abnormal_non_vf",
    "qrs_status": "abnormal",
}

SUSPECTED = {
    "ecg_quality": "valid",
    "rhythm_classification": "vf_compatible",
    "qrs_status": "not_organized",
}

ARREST = {
    **SUSPECTED,
    "heart_rate_status": "not_reliably_calculable",
    "spo2_status": "unreliable_without_perfusion",
    "respiratory_rate_status": "not_assessed",
    "blood_pressure_status": "unmeasurable",
    "pulse_status": "absent",
    "responsiveness_status": "unresponsive",
    "breathing_status": "absent",
}

INVALID = {
    **NORMAL,
    "ecg_quality": "invalid",
    "rhythm_classification": "uninterpretable",
    "qrs_status": "uninterpretable",
    "heart_rate_status": "unreliable",
    "spo2_status": "not_assessed",
    "respiratory_rate_status": "not_assessed",
    "blood_pressure_status": "not_assessed",
    "pulse_status": "not_assessed",
    "responsiveness_status": "not_assessed",
    "breathing_status": "not_assessed",
}


def test_rule_engine_classifies_the_five_configured_states():
    assert evaluate_rules(NORMAL).candidate_state == "NORMAL_MONITORING"
    assert evaluate_rules(ABNORMAL).candidate_state == "ABNORMAL_RHYTHM"
    assert evaluate_rules(SUSPECTED).candidate_state == "SUSPECTED_VF"
    assert evaluate_rules(ARREST).candidate_state == "VF_CARDIAC_ARREST"
    assert evaluate_rules(INVALID).candidate_state == "SIGNAL_INVALID"


def test_rule_engine_prioritizes_arrest_over_suspected_vf():
    decision = evaluate_rules(ARREST)
    assert decision.rule_id == "R01"
    assert decision.priority == 1
    assert "R02" in decision.competing_rule_ids
    assert "pulse_status" in decision.matched_variables


def test_suspected_vf_does_not_require_complementary_measurements():
    decision = evaluate_rules(SUSPECTED)
    assert decision.evaluation_status == "matched"
    assert decision.candidate_state == "SUSPECTED_VF"
    assert decision.missing_evidence == ()


def test_missing_required_evidence_is_indeterminate_not_normal():
    decision = evaluate_rules({})
    assert decision.evaluation_status == "indeterminate"
    assert decision.candidate_state is None
    assert decision.rule_id is None
    assert "ecg_quality" in decision.missing_evidence


def test_fully_evaluated_non_matching_categories_are_no_match():
    categories = {
        **NORMAL,
        "rhythm_classification": "vf_compatible",
    }
    decision = evaluate_rules(categories)
    assert decision.evaluation_status == "no_match"
    assert decision.candidate_state is None


def test_unknown_variables_and_categories_are_rejected():
    with pytest.raises(RuleInputError, match="Unknown monitoring variables"):
        evaluate_rules({"unknown_status": "value"})
    with pytest.raises(RuleInputError, match="Unknown category"):
        evaluate_rules({"ecg_quality": "not_a_real_category"})


def test_rule_decision_contains_condition_trace():
    decision = evaluate_rules(SUSPECTED)
    assert decision.trace
    assert decision.trace[1]["rule_id"] == "R02"
    assert decision.trace[1]["result"] == "matched"
    assert decision.to_dict()["trace"]


def test_state_machine_allows_configured_suspected_transition():
    machine = StateMachine()
    result = machine.apply("SUSPECTED_VF", SUSPECTED, timestamp="2026-11-15T12:00:00+00:00")
    assert result.allowed
    assert result.transition_id == "T02"
    assert machine.current_state == "SUSPECTED_VF"


def test_state_machine_retains_arrest_without_authorized_exit():
    machine = StateMachine()
    machine.apply("SUSPECTED_VF", SUSPECTED)
    arrest_result = machine.apply("VF_CARDIAC_ARREST", ARREST)
    assert arrest_result.allowed
    assert machine.current_state == "VF_CARDIAC_ARREST"

    normal_result = machine.apply("NORMAL_MONITORING", NORMAL)
    assert not normal_result.allowed
    assert normal_result.resulting_state == "VF_CARDIAC_ARREST"
    assert machine.current_state == "VF_CARDIAC_ARREST"


def test_state_machine_requires_authorized_post_event_exit():
    machine = StateMachine()
    machine.apply("VF_CARDIAC_ARREST", ARREST)
    result = machine.apply(
        "NORMAL_MONITORING",
        NORMAL,
        external_controls={
            "authorized_clinical_operator": True,
            "post_event_circulation_assessment": "completed",
        },
        timestamp="2026-11-15T12:00:01+00:00",
    )
    assert result.allowed
    assert result.transition_id == "T10"
    assert machine.current_state == "NORMAL_MONITORING"


def test_invalid_signal_transition_is_configured():
    machine = StateMachine()
    machine.apply("NORMAL_MONITORING", NORMAL)
    result = machine.apply("SIGNAL_INVALID", INVALID)
    assert result.allowed
    assert result.transition_id == "T03"
    assert machine.current_state == "SIGNAL_INVALID"


def test_monitor_keeps_candidate_and_effective_state_separate():
    monitor = Monitor()
    result = monitor.evaluate(SUSPECTED, timestamp="2026-11-15T12:00:00+00:00")
    assert result.candidate_state == "SUSPECTED_VF"
    assert result.effective_state == "SUSPECTED_VF"
    assert result.transition.allowed
    assert result.evaluation_mode == "immediate"


def test_monitor_uses_periodic_interval_without_sleeping():
    monitor = Monitor()
    first = monitor.evaluate(NORMAL, timestamp="2026-11-15T12:00:00+00:00")
    second = monitor.evaluate(NORMAL, timestamp="2026-11-15T12:00:03+00:00")
    third = monitor.evaluate(NORMAL, timestamp="2026-11-15T12:00:05+00:00")
    assert first.evaluation_mode == "periodic"
    assert not first.skipped
    assert second.skipped
    assert third.evaluation_mode == "periodic"
    assert not third.skipped
    assert len(monitor.history) == 3


def test_monitor_promotes_emergency_evidence_to_immediate_evaluation():
    monitor = Monitor()
    monitor.evaluate(NORMAL, timestamp=datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc))
    result = monitor.evaluate(ARREST, timestamp="2026-11-15T12:00:01+00:00", evaluation_mode="periodic")
    assert result.evaluation_mode == "immediate"
    assert result.effective_state == "VF_CARDIAC_ARREST"


def test_monitor_retains_state_when_evidence_is_indeterminate():
    monitor = Monitor()
    monitor.evaluate(NORMAL, timestamp="2026-11-15T12:00:00+00:00")
    result = monitor.evaluate({}, timestamp="2026-11-15T12:00:05+00:00")
    assert result.rule_decision.evaluation_status == "indeterminate"
    assert result.candidate_state is None
    assert result.effective_state == "NORMAL_MONITORING"
    assert not result.transition.allowed


def test_results_are_serializable():
    result = Monitor().evaluate(SUSPECTED, timestamp="2026-11-15T12:00:00+00:00")
    payload = result.to_dict()
    assert payload["rule_decision"]["candidate_state"] == "SUSPECTED_VF"
    assert payload["transition"]["transition_id"] == "T02"
