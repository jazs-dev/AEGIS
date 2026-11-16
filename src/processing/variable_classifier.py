"""Deterministic classification of numeric physiological measurements."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from src.processing.config_loader import Configuration, load_configuration
from src.processing.measurement_validator import MeasurementValidation, validate_measurements


class ClassificationError(ValueError):
    """Raised when classification configuration cannot be evaluated safely."""


class AmbiguousRuleError(ClassificationError):
    """Raised when more than one non-fallback rule matches a value."""


class ExpressionError(ClassificationError):
    """Raised when a configured numeric expression uses unsupported syntax."""


@dataclass(frozen=True)
class ClassificationResult:
    """Stable output contract for one classified variable."""

    variable: str
    raw_value: Any
    unit: str
    status: str
    validity: str
    matched_rule: str | None
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the result."""
        return {
            "variable": self.variable,
            "raw_value": self.raw_value,
            "unit": self.unit,
            "status": self.status,
            "validity": self.validity,
            "matched_rule": self.matched_rule,
            "explanation": self.explanation,
        }


_COMPARISON = re.compile(r"^(<=|>=|<|>)\s*(-?(?:\d+(?:\.\d*)?|\.\d+))$")


def evaluate_expression(value: float, expression: str) -> bool:
    """Evaluate only numeric comparisons combined with ``AND`` and ``OR``.

    The parser does not execute Python code and accepts no names, calls,
    parentheses, arithmetic, or other operators.  ``AND`` binds more tightly
    than ``OR`` by evaluating each OR branch as an AND group.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("Numeric expression must be a non-empty string")
    if "(" in expression or ")" in expression:
        raise ExpressionError("Parentheses are not supported in configured expressions")
    branches = expression.split(" OR ")
    if any(not branch.strip() for branch in branches):
        raise ExpressionError(f"Malformed OR expression: {expression!r}")
    return any(_evaluate_and_group(value, branch) for branch in branches)


def _evaluate_and_group(value: float, expression: str) -> bool:
    comparisons = expression.split(" AND ")
    if any(not comparison.strip() for comparison in comparisons):
        raise ExpressionError(f"Malformed AND expression: {expression!r}")
    results = []
    for comparison in comparisons:
        match = _COMPARISON.fullmatch(comparison.strip())
        if match is None:
            raise ExpressionError(f"Unsupported comparison: {comparison!r}")
        operator, number_text = match.groups()
        threshold = float(number_text)
        if operator == "<":
            results.append(value < threshold)
        elif operator == "<=":
            results.append(value <= threshold)
        elif operator == ">":
            results.append(value > threshold)
        else:
            results.append(value >= threshold)
    return all(results)


def classify_measurements(
    measurements: Mapping[str, Any],
    units: Mapping[str, str] | None = None,
    configuration: Configuration | None = None,
) -> dict[str, ClassificationResult]:
    """Classify the configured physiological measurements deterministically."""
    config = configuration or load_configuration()
    validation = validate_measurements(measurements, units, config)
    rules = config.document("classification_rules.json")["classification_rules"]
    results: dict[str, ClassificationResult] = {}

    for input_name, variable in (
        ("heart_rate", "heart_rate_status"),
        ("spo2", "spo2_status"),
        ("respiratory_rate", "respiratory_rate_status"),
    ):
        results[variable] = _classify_scalar(input_name, variable, validation[input_name], rules[variable]["rules"])

    results["blood_pressure_status"] = _classify_blood_pressure(
        validation["systolic_pressure"],
        validation["diastolic_pressure"],
        rules["blood_pressure_status"]["rules"],
    )
    return results


def _classify_scalar(
    input_name: str,
    variable: str,
    validation: MeasurementValidation,
    rules: Mapping[str, Mapping[str, Any]],
) -> ClassificationResult:
    if validation.validity == "not_assessed":
        return _result(validation, "not_assessed", None, validation.reason)
    if not validation.is_classifiable:
        return _result(validation, "invalid", "invalid", validation.reason)

    matches = [name for name, rule in rules.items() if "value" in rule and evaluate_expression(float(validation.raw_value), rule["value"])]
    if len(matches) > 1:
        raise AmbiguousRuleError(f"Multiple rules match {variable}: {matches}")
    if not matches:
        raise ClassificationError(f"No classification rule matched valid {input_name} value {validation.raw_value!r}")
    category = matches[0]
    return _result(validation, category, category, f"Matched {variable} expression {rules[category]['value']!r}")


def _classify_blood_pressure(
    systolic: MeasurementValidation,
    diastolic: MeasurementValidation,
    rules: Mapping[str, Mapping[str, Any]],
) -> ClassificationResult:
    raw_value = {"systolic_pressure": systolic.raw_value, "diastolic_pressure": diastolic.raw_value}
    if systolic.validity == "not_assessed" or diastolic.validity == "not_assessed":
        return ClassificationResult("blood_pressure_status", raw_value, systolic.unit, "not_assessed", "not_assessed", None, "Both pressure values are required")
    if not systolic.is_classifiable or not diastolic.is_classifiable:
        reason = systolic.reason if not systolic.is_classifiable else diastolic.reason
        validity = "out_of_domain" if "out_of_domain" in {systolic.validity, diastolic.validity} else "invalid"
        return ClassificationResult("blood_pressure_status", raw_value, systolic.unit, "invalid", validity, "invalid", reason)

    matches: list[str] = []
    for name, rule in rules.items():
        if "systolic" not in rule or "diastolic" not in rule:
            continue
        operator = rule.get("operator", "AND")
        if operator not in {"AND", "OR"}:
            raise ExpressionError(f"Unsupported blood pressure operator: {operator!r}")
        systolic_match = evaluate_expression(float(systolic.raw_value), rule["systolic"])
        diastolic_match = evaluate_expression(float(diastolic.raw_value), rule["diastolic"])
        if (systolic_match and diastolic_match) if operator == "AND" else (systolic_match or diastolic_match):
            matches.append(name)
    if len(matches) > 1:
        raise AmbiguousRuleError(f"Multiple blood pressure rules match: {matches}")
    if matches:
        category = matches[0]
        return ClassificationResult("blood_pressure_status", raw_value, systolic.unit, category, "valid", category, f"Matched blood pressure rule {category!r}")
    if "altered" not in rules:
        raise ClassificationError("Blood pressure has no matching rule or altered fallback")
    return ClassificationResult("blood_pressure_status", raw_value, systolic.unit, "altered", "valid", "altered", "No specific blood pressure rule matched")


def _result(validation: MeasurementValidation, status: str, matched_rule: str | None, explanation: str) -> ClassificationResult:
    return ClassificationResult(validation.variable, validation.raw_value, validation.unit, status, validation.validity, matched_rule, explanation)
