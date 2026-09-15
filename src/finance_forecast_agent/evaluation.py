from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, pstdev


@dataclass(frozen=True)
class CostModel:
    commission_bps: float = 1.0
    half_spread_bps: float = 2.0
    market_impact_bps: float = 1.0
    latency_penalty_bps: float = 0.0

    @property
    def total_bps(self) -> float:
        return (
            self.commission_bps
            + self.half_spread_bps
            + self.market_impact_bps
            + self.latency_penalty_bps
        )


def _annualized_sharpe(values: list[float]) -> float:
    vol = pstdev(values) if len(values) > 1 else 0.0
    return mean(values) / vol * sqrt(52) if vol > 0 else 0.0


def evaluate_sign_strategy(
    y_true: list[float],
    y_pred: list[float],
    *,
    cost: CostModel,
) -> dict[str, float]:
    if len(y_true) != len(y_pred):
        raise ValueError("length mismatch")
    if not y_true:
        return {
            "gross_return": 0.0,
            "net_return": 0.0,
            "cost_paid": 0.0,
            "turnover": 0.0,
            "trade_count": 0.0,
            "buy_hold_return": 0.0,
            "excess_return": 0.0,
            "gross_sharpe": 0.0,
            "net_sharpe": 0.0,
            "sharpe": 0.0,
            "hit_rate": 0.0,
        }

    positions = [1 if pred >= 0 else -1 for pred in y_pred]
    gross_period = [position * ret for position, ret in zip(positions, y_true)]

    previous = 0
    turnover_steps: list[float] = []
    for position in positions:
        turnover_steps.append(float(abs(position - previous)))
        previous = position
    per_period_cost = [
        turnover * cost.total_bps / 10000.0 for turnover in turnover_steps
    ]
    net_period = [
        gross - paid for gross, paid in zip(gross_period, per_period_cost)
    ]

    gross = sum(gross_period)
    cost_paid = sum(per_period_cost)
    net = sum(net_period)
    net_sharpe = _annualized_sharpe(net_period)
    return {
        "gross_return": gross,
        "net_return": net,
        "cost_paid": cost_paid,
        "turnover": sum(turnover_steps),
        "trade_count": float(sum(step > 0 for step in turnover_steps)),
        "buy_hold_return": sum(y_true),
        "excess_return": net - sum(y_true),
        "gross_sharpe": _annualized_sharpe(gross_period),
        "net_sharpe": net_sharpe,
        "sharpe": net_sharpe,
        "hit_rate": mean([1.0 if ret > 0 else 0.0 for ret in gross_period]),
    }


def cost_scenarios(
    y_true: list[float],
    y_pred: list[float],
) -> dict[str, dict[str, float]]:
    return {
        "zero_cost": evaluate_sign_strategy(
            y_true,
            y_pred,
            cost=CostModel(0, 0, 0, 0),
        ),
        "base_cost": evaluate_sign_strategy(y_true, y_pred, cost=CostModel()),
        "stress_cost": evaluate_sign_strategy(
            y_true,
            y_pred,
            cost=CostModel(2, 8, 5, 2),
        ),
    }
