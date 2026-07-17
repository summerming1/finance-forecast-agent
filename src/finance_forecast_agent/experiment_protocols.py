from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, ClassVar, Literal


ProtocolStatus = Literal["strict_ready", "blocked"]


@dataclass(frozen=True)
class ProtocolAudit:
    experiment_type: str
    status: ProtocolStatus
    blockers: list[str]
    warnings: list[str]
    required_artifacts: list[str]
    leakage_checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == "strict_ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_type": self.experiment_type,
            "status": self.status,
            "passed": self.passed,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "required_artifacts": self.required_artifacts,
            "leakage_checks": self.leakage_checks,
        }


class StrictProtocol:
    experiment_type: ClassVar[str]
    required_artifacts: ClassVar[tuple[str, ...]]

    def audit(self) -> ProtocolAudit:
        blockers = []
        for item in fields(self):
            value = getattr(self, item.name)
            if value is None or value == "" or value == [] or value == {}:
                blockers.append(f"{self.experiment_type} protocol is missing {item.name}")
        leakage = self.leakage_checks()
        blockers.extend(name for name, passed in leakage.items() if not passed)
        return ProtocolAudit(
            experiment_type=self.experiment_type,
            status="blocked" if blockers else "strict_ready",
            blockers=blockers,
            warnings=self.warnings(),
            required_artifacts=list(self.required_artifacts),
            leakage_checks=leakage,
        )

    def leakage_checks(self) -> dict[str, bool]:
        return {}

    def warnings(self) -> list[str]:
        return []


@dataclass(frozen=True)
class SignalBacktestProtocol(StrictProtocol):
    experiment_type: ClassVar[str] = "signal_backtest"
    required_artifacts: ClassVar[tuple[str, ...]] = (
        "positions",
        "turnover",
        "gross_returns",
        "costs",
        "net_returns",
        "performance_summary",
    )

    signal_timestamp: str
    execution_timestamp: str
    holding_period: str
    position_rule: str
    rebalance_rule: str
    transaction_cost_bps: float
    slippage_bps: float
    shorting_rule: str
    corporate_action_policy: str
    split_protocol: str
    metrics: list[str]

    def leakage_checks(self) -> dict[str, bool]:
        return {
            "signal_must_precede_execution": self.signal_timestamp != self.execution_timestamp,
            "chronological_or_purged_split_required": any(
                token in self.split_protocol.lower() for token in ("chronological", "walk", "purged")
            ),
            "net_performance_metric_required": any(
                token in " ".join(self.metrics).lower() for token in ("net", "sharpe", "drawdown")
            ),
        }


@dataclass(frozen=True)
class CrossSectionalProtocol(StrictProtocol):
    experiment_type: ClassVar[str] = "cross_sectional"
    required_artifacts: ClassVar[tuple[str, ...]] = (
        "point_in_time_panel",
        "formation_assignments",
        "portfolio_returns",
        "factor_adjusted_alpha",
        "inference_summary",
    )

    market: str
    universe_rule: str
    point_in_time_policy: str
    characteristic_lag: str
    missing_value_policy: str
    normalization_rule: str
    portfolio_formation: str
    weighting_rule: str
    rebalance_rule: str
    inference_protocol: str
    delisting_return_policy: str

    def leakage_checks(self) -> dict[str, bool]:
        point_in_time = self.point_in_time_policy.lower()
        return {
            "point_in_time_features_required": "point" in point_in_time or "as-of" in point_in_time,
            "characteristics_must_be_lagged": self.characteristic_lag.lower() not in {"none", "0", "same day"},
            "inference_protocol_required": any(
                token in self.inference_protocol.lower()
                for token in ("newey", "bootstrap", "cluster", "fama-macbeth", "hac")
            ),
        }


@dataclass(frozen=True)
class PortfolioRLProtocol(StrictProtocol):
    experiment_type: ClassVar[str] = "portfolio_rl"
    required_artifacts: ClassVar[tuple[str, ...]] = (
        "environment_trace",
        "actions",
        "portfolio_weights",
        "costs",
        "rewards",
        "seed_results",
        "baseline_comparison",
    )

    state_spec: str
    action_spec: str
    reward_spec: str
    transition_timing: str
    portfolio_constraints: str
    transaction_cost_bps: float
    training_seeds: list[int]
    evaluation_seeds: list[int]
    baseline_policies: list[str]
    train_test_protocol: str

    def leakage_checks(self) -> dict[str, bool]:
        return {
            "state_action_timing_declared": any(
                token in self.transition_timing.lower() for token in ("t+1", "next", "after")
            ),
            "independent_evaluation_seeds_required": bool(
                set(self.evaluation_seeds) - set(self.training_seeds)
            ),
            "chronological_evaluation_required": any(
                token in self.train_test_protocol.lower() for token in ("chronological", "walk", "out-of-sample")
            ),
        }

    def warnings(self) -> list[str]:
        return [] if len(self.evaluation_seeds) >= 3 else ["fewer than three evaluation seeds"]


_PROTOCOL_TYPES: dict[str, type[StrictProtocol]] = {
    "signal_backtest": SignalBacktestProtocol,
    "cross_sectional": CrossSectionalProtocol,
    "portfolio_rl": PortfolioRLProtocol,
}


def audit_experiment_protocol(experiment_type: str, payload: dict[str, Any]) -> ProtocolAudit:
    protocol_type = _PROTOCOL_TYPES.get(experiment_type)
    if protocol_type is None:
        return ProtocolAudit(experiment_type, "strict_ready", [], [], [], {})
    allowed = {item.name for item in fields(protocol_type)}
    try:
        protocol = protocol_type(**{key: value for key, value in payload.items() if key in allowed})
    except TypeError as exc:
        return ProtocolAudit(
            experiment_type,
            "blocked",
            [f"invalid {experiment_type} protocol: {exc}"],
            [],
            list(protocol_type.required_artifacts),
            {},
        )
    return protocol.audit()
