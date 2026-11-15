from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from src.processing.config_loader import (
    Configuration,
    ConfigurationFileError,
    load_configuration,
)
from src.processing.variable_classifier import (
    AmbiguousRuleError,
    ExpressionError,
    classify_measurements,
    evaluate_expression,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def configuration():
    return load_configuration()


def values(**overrides):
    measurements = {
        "heart_rate": 72,
        "spo2": 98,
        "respiratory_rate": 16,
        "systolic_pressure": 110,
        "diastolic_pressure": 70,
    }
    measurements.update(overrides)
    return measurements


def test_normal_values_are_classified(configuration):
    result = classify_measurements(values(), configuration=configuration)
    assert result["heart_rate_status"].status == "normal_for_context"
    assert result["spo2_status"].status == "adequate"
    assert result["respiratory_rate_status"].status == "normal_for_context"
    assert result["blood_pressure_status"].status == "stable"


@pytest.mark.parametrize(
    ("heart_rate", "expected"),
    [(59, "bradycardia"), (60, "normal_for_context"), (100, "normal_for_context"), (101, "tachycardia")],
)
def test_heart_rate_boundaries(configuration, heart_rate, expected):
    result = classify_measurements(values(heart_rate=heart_rate), configuration=configuration)
    assert result["heart_rate_status"].status == expected


@pytest.mark.parametrize(
    ("spo2", "expected"),
    [(0, "altered"), (94.9, "altered"), (95, "adequate"), (100, "adequate")],
)
def test_spo2_boundaries(configuration, spo2, expected):
    result = classify_measurements(values(spo2=spo2), configuration=configuration)
    assert result["spo2_status"].status == expected


@pytest.mark.parametrize(
    ("respiratory_rate", "expected"),
    [(0, "bradypnea"), (11.9, "bradypnea"), (12, "normal_for_context"), (20, "normal_for_context"), (20.1, "tachypnea")],
)
def test_respiratory_rate_boundaries(configuration, respiratory_rate, expected):
    result = classify_measurements(values(respiratory_rate=respiratory_rate), configuration=configuration)
    assert result["respiratory_rate_status"].status == expected


@pytest.mark.parametrize(
    ("systolic_pressure", "diastolic_pressure", "expected"),
    [(110, 70, "stable"), (120, 70, "elevated"), (89, 70, "low"), (110, 59, "low"), (130, 70, "altered")],
)
def test_blood_pressure_rules(configuration, systolic_pressure, diastolic_pressure, expected):
    result = classify_measurements(
        values(systolic_pressure=systolic_pressure, diastolic_pressure=diastolic_pressure),
        configuration=configuration,
    )
    assert result["blood_pressure_status"].status == expected


def test_missing_values_are_not_assessed(configuration):
    result = classify_measurements(values(heart_rate=None, spo2=None, respiratory_rate=None, systolic_pressure=None, diastolic_pressure=None), configuration=configuration)
    assert result["heart_rate_status"].validity == "not_assessed"
    assert result["heart_rate_status"].status == "not_assessed"
    assert result["blood_pressure_status"].validity == "not_assessed"
    assert result["blood_pressure_status"].raw_value == {"systolic_pressure": None, "diastolic_pressure": None}


@pytest.mark.parametrize("field", ["heart_rate", "spo2", "respiratory_rate", "systolic_pressure", "diastolic_pressure"])
def test_non_numeric_values_are_invalid(configuration, field):
    result = classify_measurements(values(**{field: "not-a-number"}), configuration=configuration)
    status_key = "blood_pressure_status" if "pressure" in field else f"{field}_status"
    assert result[status_key].validity == "invalid"
    assert result[status_key].status == "invalid"


@pytest.mark.parametrize(
    ("field", "expected"),
    [("heart_rate", "invalid"), ("spo2", "invalid"), ("respiratory_rate", "invalid")],
)
def test_non_finite_values_are_invalid(configuration, field, expected):
    result = classify_measurements(values(**{field: float("nan")}), configuration=configuration)
    assert result[f"{field}_status"].status == expected
    result = classify_measurements(values(**{field: float("inf")}), configuration=configuration)
    assert result[f"{field}_status"].status == expected


def test_domain_and_pressure_consistency_are_rejected(configuration):
    result = classify_measurements(values(spo2=101), configuration=configuration)
    assert result["spo2_status"].validity == "out_of_domain"
    assert result["spo2_status"].status == "invalid"

    result = classify_measurements(values(systolic_pressure=60, diastolic_pressure=80), configuration=configuration)
    assert result["blood_pressure_status"].validity == "out_of_domain"
    assert result["blood_pressure_status"].status == "invalid"


def test_units_are_checked_when_provided(configuration):
    result = classify_measurements(values(), units={"heart_rate": "%"}, configuration=configuration)
    assert result["heart_rate_status"].validity == "invalid"
    assert result["heart_rate_status"].status == "invalid"


def test_output_contract_is_serializable(configuration):
    result = classify_measurements(values(), configuration=configuration)["heart_rate_status"]
    payload = result.to_dict()
    assert payload == {
        "variable": "heart_rate_status",
        "raw_value": 72,
        "unit": "bpm",
        "status": "normal_for_context",
        "validity": "valid",
        "matched_rule": "normal_for_context",
        "explanation": "Matched heart_rate_status expression '>=60 AND <=100'",
    }
    json.dumps(payload)


def test_expression_evaluator_supports_only_configured_operators():
    assert evaluate_expression(60, ">=60 AND <=100")
    assert evaluate_expression(101, ">100 OR <0")
    assert not evaluate_expression(50, ">100 OR <0")
    with pytest.raises(ExpressionError):
        evaluate_expression(1, "__import__('os')")
    with pytest.raises(ExpressionError):
        evaluate_expression(1, ">=0 XOR <=1")


def test_ambiguous_rules_are_rejected(configuration):
    documents = deepcopy(configuration.documents)
    documents["classification_rules.json"]["classification_rules"]["heart_rate_status"]["rules"]["overlap"] = {
        "value": ">=60"
    }
    ambiguous = Configuration(documents, configuration.directory)
    with pytest.raises(AmbiguousRuleError):
        classify_measurements(values(), configuration=ambiguous)


def test_missing_configuration_file_has_clear_error(tmp_path):
    config_copy = tmp_path / "config"
    shutil.copytree(ROOT / "config", config_copy)
    (config_copy / "vf_rules.json").unlink()
    with pytest.raises(ConfigurationFileError, match="Missing configuration file"):
        load_configuration(config_copy)


def test_invalid_configuration_json_has_clear_error(tmp_path):
    config_copy = tmp_path / "config"
    shutil.copytree(ROOT / "config", config_copy)
    (config_copy / "classification_rules.json").write_text("{invalid", encoding="utf-8")
    with pytest.raises(ConfigurationFileError, match="Invalid JSON"):
        load_configuration(config_copy)
