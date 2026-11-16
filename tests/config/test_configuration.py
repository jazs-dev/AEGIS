import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
CONFIG_FILES = (
    "fv_states.json",
    "variable_definitions.json",
    "classification_rules.json",
    "ecg_classification.json",
    "vf_rules.json",
    "vf_transitions.json",
)


@pytest.fixture(scope="module")
def configs():
    loaded = {}
    for filename in CONFIG_FILES:
        with (CONFIG_DIR / filename).open(encoding="utf-8") as stream:
            loaded[filename] = json.load(stream)
    return loaded


def test_all_configuration_files_are_valid_json(configs):
    assert set(configs) == set(CONFIG_FILES)


def test_variable_definitions_are_complete(configs):
    definitions = configs["variable_definitions.json"]["variables"]
    assert definitions
    for name, definition in definitions.items():
        assert definition["allowed_values"]
        assert all(isinstance(value, str) for value in definition["allowed_values"])
        assert all("_or_" not in value for value in definition["allowed_values"])
        assert all(" or " not in value for value in definition["allowed_values"])


def test_classification_rule_variables_and_categories_exist(configs):
    definitions = configs["variable_definitions.json"]["variables"]
    rules = configs["classification_rules.json"]["classification_rules"]
    assert set(rules) <= set(definitions)
    for variable, definition in rules.items():
        for category in definition["rules"]:
            assert category in definitions[variable]["allowed_values"]


def test_vf_rule_references_are_defined(configs):
    definitions = configs["variable_definitions.json"]["variables"]
    rules = configs["vf_rules.json"]
    referenced_variables = set(rules["evaluation"]["base_sensor_variables"]) | set(
        rules["evaluation"]["additional_clinical_evidence_variables"]
    )
    assert referenced_variables == set(definitions)

    for rule in rules["rules"]:
        for section in ("required", "supporting"):
            for variable, categories in rule.get(section, {}).items():
                assert variable in definitions
                assert set(categories) <= set(definitions[variable]["allowed_values"])
                assert all("_or_" not in category for category in categories)


def test_states_use_only_defined_atomic_categories(configs):
    definitions = configs["variable_definitions.json"]["variables"]
    states = configs["fv_states.json"]["states"]
    assert set(states)
    for state in states.values():
        assert set(state) == set(definitions)
        for variable, category in state.items():
            assert category in definitions[variable]["allowed_values"]
            assert "_or_" not in category


def test_rule_outputs_and_priorities_are_consistent(configs):
    states = set(configs["fv_states.json"]["states"])
    rules = configs["vf_rules.json"]["rules"]
    priorities = [rule["priority"] for rule in rules]
    assert len(priorities) == len(set(priorities))
    assert priorities == sorted(priorities)
    assert {rule["output_state"] for rule in rules} <= states


def test_transitions_reference_only_declared_states_and_priorities(configs):
    states = set(configs["fv_states.json"]["states"])
    transitions = configs["vf_transitions.json"]
    assert transitions["initial_state"] in states
    assert set(transitions["priority_order"]) == states

    for transition in transitions["transitions"]:
        assert set(transition["from"]) <= states
        assert transition["to"] in states
        assert isinstance(transition["priority"], int)
    assert any(
        transition["from"] == ["VF_CARDIAC_ARREST"]
        and transition["to"] == "VF_CARDIAC_ARREST"
        for transition in transitions["transitions"]
    )


def test_transition_conditions_use_defined_variables_or_explicit_controls(configs):
    definitions = configs["variable_definitions.json"]["variables"]
    transitions = configs["vf_transitions.json"]
    controls = {
        "authorized_clinical_operator": {True},
        "post_event_circulation_assessment": {"completed"},
    }
    for transition in transitions["transitions"]:
        conditions = transition["conditions"]["all_of"]
        for variable, categories in conditions.items():
            if variable in definitions:
                assert set(categories) <= set(definitions[variable]["allowed_values"])
            else:
                assert variable in controls
                assert set(categories) <= controls[variable]


def test_high_priority_rules_preserve_clinical_separation(configs):
    rules = configs["vf_rules.json"]["rules"]
    arrest = next(rule for rule in rules if rule["output_state"] == "VF_CARDIAC_ARREST")
    suspected = next(rule for rule in rules if rule["output_state"] == "SUSPECTED_VF")
    assert arrest["priority"] < suspected["priority"]
    assert set(arrest["required"]) >= {
        "ecg_quality",
        "rhythm_classification",
        "qrs_status",
        "pulse_status",
        "responsiveness_status",
        "breathing_status",
    }
    assert "blood_pressure_status" not in suspected["required"]
    assert "spo2_status" not in suspected["required"]
