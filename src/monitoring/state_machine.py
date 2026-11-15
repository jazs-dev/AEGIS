"""Finite-state transition control driven by ``vf_transitions.json``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from src.processing.config_loader import Configuration, load_configuration


class TransitionError(ValueError):
    """Raised when a requested state or control input is invalid."""


@dataclass(frozen=True)
class TransitionResult:
    """Traceable result of one requested state transition."""

    previous_state: str
    candidate_state: str | None
    resulting_state: str
    allowed: bool
    transition_id: str | None
    priority: int | None
    evaluation_mode: str
    timestamp: str
    conditions: tuple[dict[str, Any], ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable transition payload."""
        return {
            "previous_state": self.previous_state,
            "candidate_state": self.candidate_state,
            "resulting_state": self.resulting_state,
            "allowed": self.allowed,
            "transition_id": self.transition_id,
            "priority": self.priority,
            "evaluation_mode": self.evaluation_mode,
            "timestamp": self.timestamp,
            "conditions": list(self.conditions),
            "reason": self.reason,
        }


class StateMachine:
    """Stateful finite-state controller with externally supplied timestamps."""

    def __init__(self, configuration: Configuration | None = None) -> None:
        self.configuration = configuration or load_configuration()
        transitions = self.configuration.document("vf_transitions.json")
        self._states = set(self.configuration.document("fv_states.json")["states"])
        self._transitions = transitions["transitions"]
        self._current_state = transitions["initial_state"]
        self._history: list[TransitionResult] = []

    @property
    def current_state(self) -> str:
        """Return the effective state."""
        return self._current_state

    @property
    def history(self) -> tuple[TransitionResult, ...]:
        """Return an immutable view of transition history."""
        return tuple(self._history)

    def apply(
        self,
        candidate_state: str | None,
        categories: Mapping[str, str],
        external_controls: Mapping[str, Any] | None = None,
        timestamp: datetime | str | None = None,
        evaluation_mode: str = "immediate",
    ) -> TransitionResult:
        """Apply a configured transition or retain the current state.

        No transition is inferred from a candidate alone: every condition in
        the matching JSON transition must be satisfied.  In particular, all
        exits from ``VF_CARDIAC_ARREST`` require the configured external
        authorization and post-event assessment.
        """
        if candidate_state is not None and candidate_state not in self._states:
            raise TransitionError(f"Unknown candidate state: {candidate_state}")
        if evaluation_mode not in {"periodic", "immediate", "periodic_or_on_new_evidence"}:
            raise TransitionError(f"Unknown evaluation mode: {evaluation_mode}")
        stamp = _timestamp(timestamp)
        controls = external_controls or {}
        candidates = [
            transition
            for transition in self._transitions
            if self._current_state in transition["from"] and transition["to"] == candidate_state
        ]
        candidates.sort(key=lambda transition: (transition["priority"], transition["id"]))
        if not candidates:
            result = TransitionResult(
                self._current_state,
                candidate_state,
                self._current_state,
                False,
                None,
                None,
                evaluation_mode,
                stamp,
                (),
                "No configured transition permits this candidate from the current state",
            )
            self._history.append(result)
            return result

        for transition in candidates:
            condition_result = _evaluate_conditions(transition["conditions"]["all_of"], categories, controls)
            if condition_result["result"] == "matched":
                result = TransitionResult(
                    self._current_state,
                    candidate_state,
                    transition["to"],
                    True,
                    transition["id"],
                    transition["priority"],
                    evaluation_mode,
                    stamp,
                    tuple(condition_result["trace"]),
                    f"Transition {transition['id']} permitted",
                )
                self._current_state = transition["to"]
                self._history.append(result)
                return result

        first = candidates[0]
        condition_result = _evaluate_conditions(first["conditions"]["all_of"], categories, controls)
        result = TransitionResult(
            self._current_state,
            candidate_state,
            self._current_state,
            False,
            first["id"],
            first["priority"],
            evaluation_mode,
            stamp,
            tuple(condition_result["trace"]),
            "Transition conditions were not satisfied",
        )
        self._history.append(result)
        return result


def _evaluate_conditions(
    conditions: Mapping[str, list[Any]],
    categories: Mapping[str, str],
    controls: Mapping[str, Any],
) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []
    for variable, expected in conditions.items():
        received = controls[variable] if variable in controls else categories.get(variable)
        matched = received in expected
        trace.append({"variable": variable, "received": received, "expected": list(expected), "result": "matched" if matched else "not_satisfied"})
        if not matched:
            return {"result": "not_satisfied", "trace": trace}
    return {"result": "matched", "trace": trace}


def _timestamp(timestamp: datetime | str | None) -> str:
    if timestamp is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    if isinstance(timestamp, str) and timestamp:
        return timestamp
    raise ValueError("timestamp must be a datetime, a non-empty ISO string, or None")
