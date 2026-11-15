"""Load and validate the declarative monitoring configuration.

This module deliberately has no Streamlit dependency.  It is the boundary
between JSON configuration and the deterministic processing layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


CONFIG_FILENAMES = (
    "fv_states.json",
    "variable_definitions.json",
    "classification_rules.json",
    "ecg_classification.json",
    "vf_rules.json",
    "vf_transitions.json",
)


class ConfigurationError(ValueError):
    """Raised when the configuration is missing or structurally inconsistent."""


class ConfigurationFileError(ConfigurationError):
    """Raised when a configuration file cannot be read or parsed as JSON."""


@dataclass(frozen=True)
class Configuration:
    """Validated configuration documents keyed by their filename."""

    documents: Mapping[str, dict[str, Any]]
    directory: Path

    def document(self, filename: str) -> dict[str, Any]:
        """Return one loaded document by its configured filename."""
        try:
            return self.documents[filename]
        except KeyError as exc:
            raise ConfigurationError(f"Configuration document is not loaded: {filename}") from exc

    @property
    def variables(self) -> dict[str, Any]:
        """Return the declared physiological and clinical variables."""
        return self.document("variable_definitions.json")["variables"]


def default_config_directory() -> Path:
    """Return the repository ``config/`` directory independent of the CWD."""
    return Path(__file__).resolve().parents[2] / "config"


def load_configuration(config_directory: str | Path | None = None) -> Configuration:
    """Load all six configuration documents and validate cross-references.

    Args:
        config_directory: Optional directory override, useful for tests.  When
            omitted, the path is resolved relative to this module's repository.

    Raises:
        ConfigurationFileError: if a file is missing, unreadable, or invalid JSON.
        ConfigurationError: if a required structure or cross-reference is invalid.
    """
    directory = Path(config_directory) if config_directory is not None else default_config_directory()
    if not directory.is_dir():
        raise ConfigurationFileError(f"Configuration directory does not exist: {directory}")

    documents: dict[str, dict[str, Any]] = {}
    for filename in CONFIG_FILENAMES:
        path = directory / filename
        if not path.is_file():
            raise ConfigurationFileError(f"Missing configuration file: {path}")
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigurationFileError(f"Unable to read configuration file {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            location = f"line {exc.lineno}, column {exc.colno}"
            raise ConfigurationFileError(f"Invalid JSON in {path} ({location}): {exc.msg}") from exc
        if not isinstance(loaded, dict):
            raise ConfigurationError(f"Configuration document must be an object: {path}")
        documents[filename] = loaded

    configuration = Configuration(documents=documents, directory=directory.resolve())
    _validate_configuration(configuration)
    return configuration


def _validate_configuration(configuration: Configuration) -> None:
    variables_document = configuration.document("variable_definitions.json")
    variables = variables_document.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise ConfigurationError("variable_definitions.json must contain a non-empty 'variables' object")

    for variable, definition in variables.items():
        allowed = definition.get("allowed_values") if isinstance(definition, dict) else None
        if not isinstance(allowed, dict) or not allowed:
            raise ConfigurationError(f"Variable {variable!r} must define non-empty allowed_values")

    classification = configuration.document("classification_rules.json").get("classification_rules")
    if not isinstance(classification, dict):
        raise ConfigurationError("classification_rules.json must contain 'classification_rules'")
    for variable, ruleset in classification.items():
        _require_variable(variable, variables, "classification_rules.json")
        if not isinstance(ruleset, dict) or not isinstance(ruleset.get("rules"), dict):
            raise ConfigurationError(f"Classification rules for {variable!r} must contain a 'rules' object")
        for category in ruleset["rules"]:
            _require_category(variable, category, variables, "classification_rules.json")

    ecg_classification = configuration.document("ecg_classification.json").get("classifications")
    if not isinstance(ecg_classification, dict) or set(ecg_classification) != {
        "ecg_quality",
        "qrs_status",
        "rhythm_classification",
    }:
        raise ConfigurationError("ecg_classification.json must define quality, QRS, and rhythm classifications")
    for classification_name, definition in ecg_classification.items():
        if not isinstance(definition, dict) or not isinstance(definition.get("input_features"), list):
            raise ConfigurationError(f"ECG classification {classification_name!r} must define input_features")
        if not isinstance(definition.get("outputs"), dict) or not definition["outputs"]:
            raise ConfigurationError(f"ECG classification {classification_name!r} must define outputs")
        for category in definition["outputs"]:
            _require_category(classification_name, category, variables, "ecg_classification.json")

    states_document = configuration.document("fv_states.json")
    states = states_document.get("states")
    if not isinstance(states, dict) or not states:
        raise ConfigurationError("fv_states.json must contain a non-empty 'states' object")
    for state_name, profile in states.items():
        if not isinstance(profile, dict):
            raise ConfigurationError(f"State {state_name!r} must be an object")
        if set(profile) != set(variables):
            raise ConfigurationError(f"State {state_name!r} must define exactly the configured variables")
        for variable, category in profile.items():
            _require_category(variable, category, variables, "fv_states.json")

    rules_document = configuration.document("vf_rules.json")
    evaluation = rules_document.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ConfigurationError("vf_rules.json must contain 'evaluation'")
    declared_variables = set(evaluation.get("base_sensor_variables", [])) | set(
        evaluation.get("additional_clinical_evidence_variables", [])
    )
    if declared_variables != set(variables):
        raise ConfigurationError("vf_rules.json evaluation variables do not match variable_definitions.json")
    vf_rules = rules_document.get("rules")
    if not isinstance(vf_rules, list) or not vf_rules:
        raise ConfigurationError("vf_rules.json must contain a non-empty 'rules' list")
    for rule in vf_rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("output_state"), str):
            raise ConfigurationError("Every VF rule must define an output_state")
        if rule["output_state"] not in states:
            raise ConfigurationError(f"VF rule references unknown state: {rule['output_state']}")
        for section_name in ("required", "supporting"):
            section = rule.get(section_name, {})
            if not isinstance(section, dict):
                raise ConfigurationError(f"VF rule {rule.get('id')} has invalid {section_name} section")
            for variable, categories in section.items():
                _validate_category_list(variable, categories, variables, "vf_rules.json")

    transitions = configuration.document("vf_transitions.json")
    if transitions.get("initial_state") not in states:
        raise ConfigurationError("vf_transitions.json initial_state is not declared in fv_states.json")
    if set(transitions.get("priority_order", [])) != set(states):
        raise ConfigurationError("vf_transitions.json priority_order must contain exactly all states")
    transition_list = transitions.get("transitions")
    if not isinstance(transition_list, list) or not transition_list:
        raise ConfigurationError("vf_transitions.json must contain a non-empty 'transitions' list")
    for transition in transition_list:
        if not isinstance(transition, dict):
            raise ConfigurationError("Every state transition must be an object")
        if not set(transition.get("from", [])) <= set(states):
            raise ConfigurationError(f"Transition {transition.get('id')} references an unknown source state")
        if transition.get("to") not in states:
            raise ConfigurationError(f"Transition {transition.get('id')} references an unknown target state")
        conditions = transition.get("conditions", {}).get("all_of", {})
        if not isinstance(conditions, dict):
            raise ConfigurationError(f"Transition {transition.get('id')} has invalid conditions")
        for variable, categories in conditions.items():
            if variable in variables:
                _validate_category_list(variable, categories, variables, "vf_transitions.json")
            elif variable not in {"authorized_clinical_operator", "post_event_circulation_assessment"}:
                raise ConfigurationError(f"Transition references unknown input: {variable}")


def _require_variable(variable: str, variables: Mapping[str, Any], source: str) -> None:
    if variable not in variables:
        raise ConfigurationError(f"{source} references unknown variable: {variable}")


def _require_category(variable: str, category: str, variables: Mapping[str, Any], source: str) -> None:
    _require_variable(variable, variables, source)
    if category not in variables[variable]["allowed_values"]:
        raise ConfigurationError(f"{source} references unknown category {category!r} for {variable!r}")


def _validate_category_list(
    variable: str,
    categories: Any,
    variables: Mapping[str, Any],
    source: str,
) -> None:
    if not isinstance(categories, list) or not categories:
        raise ConfigurationError(f"{source} categories for {variable!r} must be a non-empty list")
    for category in categories:
        _require_category(variable, category, variables, source)
