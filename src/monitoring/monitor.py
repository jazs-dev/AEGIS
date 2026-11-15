"""Coordinator for rule evaluation, state transitions, and history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.monitoring.rule_engine import RuleDecision, evaluate_rules
from src.monitoring.state_machine import StateMachine, TransitionResult
from src.processing.config_loader import Configuration, load_configuration


@dataclass(frozen=True)
class MonitorResult:
    """One monitor evaluation with candidate and effective state separated."""

    timestamp: str
    evaluation_mode: str
    candidate_state: str | None
    effective_state: str
    rule_decision: RuleDecision | None
    transition: TransitionResult | None
    skipped: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable monitoring payload."""
        return {
            "timestamp": self.timestamp,
            "evaluation_mode": self.evaluation_mode,
            "candidate_state": self.candidate_state,
            "effective_state": self.effective_state,
            "rule_decision": self.rule_decision.to_dict() if self.rule_decision else None,
            "transition": self.transition.to_dict() if self.transition else None,
            "skipped": self.skipped,
            "reason": self.reason,
        }


class Monitor:
    """Coordinate deterministic rule and finite-state evaluations."""

    def __init__(self, configuration: Configuration | None = None) -> None:
        self.configuration = configuration or load_configuration()
        self.state_machine = StateMachine(self.configuration)
        self._history: list[MonitorResult] = []
        self._last_periodic_at: datetime | None = None
        self._periodic_interval = timedelta(
            seconds=self.configuration.document("vf_transitions.json")["evaluation"]["periodic_monitoring"]["interval_seconds"]
        )

    @property
    def current_state(self) -> str:
        """Return the state currently held by the finite-state machine."""
        return self.state_machine.current_state

    @property
    def history(self) -> tuple[MonitorResult, ...]:
        """Return all completed and skipped evaluations."""
        return tuple(self._history)

    def evaluate(
        self,
        categories: Mapping[str, str],
        timestamp: datetime | str | None = None,
        evaluation_mode: str = "auto",
        external_controls: Mapping[str, Any] | None = None,
    ) -> MonitorResult:
        """Evaluate categories and request a configured state transition.

        Timestamps are supplied by callers for reproducible tests.  ``auto``
        selects immediate evaluation for suspected/emergency evidence and
        periodic evaluation otherwise.  No sleeping or wall-clock waiting is
        used.
        """
        stamp, stamp_datetime = _normalize_timestamp(timestamp)
        rule_decision = evaluate_rules(categories, self.configuration, stamp)
        mode = self._select_mode(rule_decision, categories, evaluation_mode)

        if mode == "periodic" and self._last_periodic_at is not None and stamp_datetime - self._last_periodic_at < self._periodic_interval:
            result = MonitorResult(stamp, mode, rule_decision.candidate_state, self.current_state, rule_decision, None, True, "Periodic interval has not elapsed")
            self._history.append(result)
            return result
        if mode == "periodic":
            self._last_periodic_at = stamp_datetime

        transition = self.state_machine.apply(
            rule_decision.candidate_state,
            categories,
            external_controls,
            stamp,
            mode,
        )
        result = MonitorResult(stamp, mode, rule_decision.candidate_state, transition.resulting_state, rule_decision, transition, False, transition.reason)
        self._history.append(result)
        return result

    def _select_mode(self, decision: RuleDecision, categories: Mapping[str, str], requested: str) -> str:
        if requested not in {"auto", "periodic", "immediate"}:
            raise ValueError(f"Unknown monitor evaluation mode: {requested}")
        emergency_evidence = decision.candidate_state in {"SUSPECTED_VF", "VF_CARDIAC_ARREST"} or self.current_state == "VF_CARDIAC_ARREST"
        emergency_evidence = emergency_evidence or (
            categories.get("ecg_quality") == "valid" and categories.get("rhythm_classification") == "vf_compatible"
        )
        if requested == "auto":
            return "immediate" if emergency_evidence else "periodic"
        if requested == "periodic" and emergency_evidence:
            return "immediate"
        return requested


def _normalize_timestamp(timestamp: datetime | str | None) -> tuple[str, datetime]:
    if timestamp is None:
        value = datetime.now(timezone.utc)
        return value.isoformat(), value
    if isinstance(timestamp, datetime):
        return timestamp.isoformat(), timestamp
    if isinstance(timestamp, str) and timestamp:
        try:
            value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"Invalid ISO timestamp: {timestamp!r}") from exc
        return timestamp, value
    raise ValueError("timestamp must be a datetime, a non-empty ISO string, or None")
