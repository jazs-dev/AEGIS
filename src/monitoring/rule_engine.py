"""Deterministic evaluation of the configured VF decision rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from src.processing.config_loader import Configuration, load_configuration


class RuleInputError(ValueError):
    """Raised when an input variable or category is not declared in config."""


@dataclass(frozen=True)
class RuleDecision:
    """Traceable result of evaluating all configured rules."""

    evaluation_status: str
    candidate_state: str | None
    rule_id: str | None
    priority: int | None
    matched_variables: tuple[str, ...]
    blocking_variables: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    invalid_evidence: tuple[str, ...]
    supporting_matches: tuple[str, ...]
    competing_rule_ids: tuple[str, ...]
    explanation: str
    timestamp: str
    trace: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable decision payload."""
        return {
            "evaluation_status": self.evaluation_status,
            "candidate_state": self.candidate_state,
            "rule_id": self.rule_id,
            "priority": self.priority,
            "matched_variables": list(self.matched_variables),
            "blocking_variables": list(self.blocking_variables),
            "missing_evidence": list(self.missing_evidence),
            "invalid_evidence": list(self.invalid_evidence),
            "supporting_matches": list(self.supporting_matches),
            "competing_rule_ids": list(self.competing_rule_ids),
            "explanation": self.explanation,
            "timestamp": self.timestamp,
            "trace": list(self.trace),
        }


def evaluate_rules(
    categories: Mapping[str, str],
    configuration: Configuration | None = None,
    timestamp: datetime | str | None = None,
) -> RuleDecision:
    """Evaluate configured rules in ascending priority order.

    Missing or ``not_assessed`` required evidence makes a rule indeterminate;
    it is not treated as a mismatch.  Unknown variables and categories are
    input errors.  When multiple rules match, the configured numeric priority
    selects the result and the other matches are retained in the trace.
    """
    config = configuration or load_configuration()
    _validate_category_input(categories, config)
    rules = sorted(config.document("vf_rules.json")["rules"], key=lambda rule: (rule["priority"], rule["id"]))
    traces: list[dict[str, Any]] = []
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    indeterminate: list[dict[str, Any]] = []

    for rule in rules:
        trace = _evaluate_rule(rule, categories)
        traces.append(trace)
        if trace["result"] == "matched":
            matches.append((rule, trace))
        elif trace["result"] == "indeterminate":
            indeterminate.append(trace)

    stamp = _timestamp(timestamp)
    if matches:
        selected, selected_trace = matches[0]
        competing = tuple(rule["id"] for rule, _ in matches[1:])
        return RuleDecision(
            evaluation_status="matched",
            candidate_state=selected["output_state"],
            rule_id=selected["id"],
            priority=selected["priority"],
            matched_variables=tuple(selected_trace["matched_variables"]),
            blocking_variables=(),
            missing_evidence=tuple(selected_trace["missing_evidence"]),
            invalid_evidence=tuple(selected_trace["invalid_evidence"]),
            supporting_matches=tuple(selected_trace["supporting_matches"]),
            competing_rule_ids=competing,
            explanation=f"Rule {selected['id']} matched at priority {selected['priority']}",
            timestamp=stamp,
            trace=tuple(traces),
        )

    if indeterminate:
        missing = _unique(item for trace in indeterminate for item in trace["missing_evidence"])
        invalid = _unique(item for trace in indeterminate for item in trace["invalid_evidence"])
        blocking = _unique(item for trace in indeterminate for item in trace["blocking_variables"])
        return RuleDecision(
            evaluation_status="indeterminate",
            candidate_state=None,
            rule_id=None,
            priority=None,
            matched_variables=(),
            blocking_variables=tuple(blocking),
            missing_evidence=tuple(missing),
            invalid_evidence=tuple(invalid),
            supporting_matches=(),
            competing_rule_ids=(),
            explanation="No rule can be evaluated because required evidence is missing or invalid",
            timestamp=stamp,
            trace=tuple(traces),
        )

    return RuleDecision(
        evaluation_status="no_match",
        candidate_state=None,
        rule_id=None,
        priority=None,
        matched_variables=(),
        blocking_variables=(),
        missing_evidence=(),
        invalid_evidence=(),
        supporting_matches=(),
        competing_rule_ids=(),
        explanation="All rules were evaluated and none matched",
        timestamp=stamp,
        trace=tuple(traces),
    )


def _validate_category_input(categories: Mapping[str, str], configuration: Configuration) -> None:
    variables = configuration.variables
    unknown_variables = set(categories) - set(variables)
    if unknown_variables:
        raise RuleInputError(f"Unknown monitoring variables: {sorted(unknown_variables)}")
    for variable, category in categories.items():
        allowed = variables[variable]["allowed_values"]
        if category not in allowed:
            raise RuleInputError(f"Unknown category {category!r} for {variable!r}")


def _evaluate_rule(rule: Mapping[str, Any], categories: Mapping[str, str]) -> dict[str, Any]:
    required = _evaluate_conditions(rule.get("required", {}), categories)
    supporting = _evaluate_conditions(rule.get("supporting", {}), categories, optional=True)
    if required["result"] == "matched":
        return {
            "rule_id": rule["id"],
            "result": "matched",
            "output_state": rule["output_state"],
            "priority": rule["priority"],
            "matched_variables": required["matched_variables"],
            "blocking_variables": [],
            "missing_evidence": required["missing_evidence"],
            "invalid_evidence": required["invalid_evidence"],
            "supporting_matches": supporting["matched_variables"],
            "supporting_trace": supporting["trace"],
        }
    if required["result"] == "indeterminate":
        return {
            "rule_id": rule["id"],
            "result": "indeterminate",
            "output_state": rule["output_state"],
            "priority": rule["priority"],
            "matched_variables": required["matched_variables"],
            "blocking_variables": required["blocking_variables"],
            "missing_evidence": required["missing_evidence"],
            "invalid_evidence": required["invalid_evidence"],
            "supporting_matches": supporting["matched_variables"],
            "supporting_trace": supporting["trace"],
        }
    return {
        "rule_id": rule["id"],
        "result": "not_satisfied",
        "output_state": rule["output_state"],
        "priority": rule["priority"],
        "matched_variables": required["matched_variables"],
        "blocking_variables": required["blocking_variables"],
        "missing_evidence": required["missing_evidence"],
        "invalid_evidence": required["invalid_evidence"],
        "supporting_matches": supporting["matched_variables"],
        "supporting_trace": supporting["trace"],
    }


def _evaluate_conditions(
    conditions: Mapping[str, list[str]],
    categories: Mapping[str, str],
    optional: bool = False,
) -> dict[str, Any]:
    matched: list[str] = []
    blocking: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    trace: list[dict[str, Any]] = []
    for variable, allowed in conditions.items():
        if variable not in categories:
            missing.append(variable)
            result = "missing"
        else:
            category = categories[variable]
            if category in allowed:
                matched.append(variable)
                result = "matched"
            elif category == "not_assessed":
                missing.append(variable)
                result = "missing"
            elif category == "invalid":
                invalid.append(variable)
                result = "invalid"
            else:
                blocking.append(variable)
                result = "not_satisfied"
        trace.append({"variable": variable, "received": categories.get(variable), "expected": list(allowed), "result": result})

    if missing or invalid:
        status = "indeterminate" if not optional else "optional_unavailable"
    elif blocking:
        status = "not_satisfied"
    else:
        status = "matched"
    return {
        "result": status,
        "matched_variables": matched,
        "blocking_variables": blocking,
        "missing_evidence": missing,
        "invalid_evidence": invalid,
        "trace": trace,
    }


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(values))


def _timestamp(timestamp: datetime | str | None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    if isinstance(timestamp, str) and timestamp:
        return timestamp
    raise ValueError("timestamp must be a datetime, a non-empty ISO string, or None")
