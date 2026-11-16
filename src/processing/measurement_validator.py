"""Validation of numeric physiological measurements.

The validator checks data quality and input consistency.  It does not classify
ECG signals, infer circulation, or make a medical diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, Mapping

from src.processing.config_loader import Configuration, load_configuration


INPUT_VARIABLES = {
    "heart_rate": "heart_rate_status",
    "spo2": "spo2_status",
    "respiratory_rate": "respiratory_rate_status",
}


@dataclass(frozen=True)
class MeasurementValidation:
    """Validation result for one scalar input measurement."""

    input_name: str
    variable: str
    raw_value: Any
    unit: str
    validity: str
    reason: str

    @property
    def is_classifiable(self) -> bool:
        """Whether the value is numeric, finite, and within its input domain."""
        return self.validity == "valid"


def validate_numeric_measurement(
    input_name: str,
    value: Any,
    variable: str,
    expected_unit: str,
    provided_unit: str | None = None,
) -> MeasurementValidation:
    """Validate one scalar physiological measurement.

    ``None`` is represented as ``not_assessed`` rather than zero.  Negative
    heart rate, SpO2, and respiratory-rate values are outside the domains
    represented by the configuration and are marked ``out_of_domain``.
    """
    if value is None:
        return MeasurementValidation(input_name, variable, value, expected_unit, "not_assessed", "Measurement is unavailable")
    if provided_unit is not None and provided_unit != expected_unit:
        return MeasurementValidation(input_name, variable, value, expected_unit, "invalid", f"Expected unit {expected_unit!r}")
    if isinstance(value, bool) or not isinstance(value, Real):
        return MeasurementValidation(input_name, variable, value, expected_unit, "invalid", "Measurement must be numeric")
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return MeasurementValidation(input_name, variable, value, expected_unit, "invalid", "Measurement must be finite")

    if variable in {"heart_rate_status", "spo2_status", "respiratory_rate_status"}:
        if numeric_value < 0 or (variable == "spo2_status" and numeric_value > 100):
            return MeasurementValidation(input_name, variable, value, expected_unit, "out_of_domain", "Measurement is outside the configured physical domain")
    return MeasurementValidation(input_name, variable, value, expected_unit, "valid", "Measurement is numeric and finite")


def validate_measurements(
    measurements: Mapping[str, Any],
    units: Mapping[str, str] | None = None,
    configuration: Configuration | None = None,
) -> dict[str, MeasurementValidation]:
    """Validate the five supported scalar inputs and return results by input name."""
    config = configuration or load_configuration()
    definitions = config.variables
    provided_units = units or {}
    results: dict[str, MeasurementValidation] = {}

    for input_name, variable in INPUT_VARIABLES.items():
        expected_unit = definitions[variable]["unit"]
        results[input_name] = validate_numeric_measurement(
            input_name,
            measurements.get(input_name),
            variable,
            expected_unit,
            provided_units.get(input_name),
        )

    systolic = validate_numeric_measurement(
        "systolic_pressure",
        measurements.get("systolic_pressure"),
        "blood_pressure_status",
        definitions["blood_pressure_status"]["unit"],
        provided_units.get("systolic_pressure"),
    )
    diastolic = validate_numeric_measurement(
        "diastolic_pressure",
        measurements.get("diastolic_pressure"),
        "blood_pressure_status",
        definitions["blood_pressure_status"]["unit"],
        provided_units.get("diastolic_pressure"),
    )
    if systolic.is_classifiable and diastolic.is_classifiable and float(systolic.raw_value) < float(diastolic.raw_value):
        reason = "Systolic pressure cannot be lower than diastolic pressure"
        systolic = MeasurementValidation(systolic.input_name, systolic.variable, systolic.raw_value, systolic.unit, "out_of_domain", reason)
        diastolic = MeasurementValidation(diastolic.input_name, diastolic.variable, diastolic.raw_value, diastolic.unit, "out_of_domain", reason)
    results["systolic_pressure"] = systolic
    results["diastolic_pressure"] = diastolic
    return results
