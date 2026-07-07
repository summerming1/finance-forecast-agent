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
        return self.commission_bps + self.half_spread_bps + self.market_impact_bps + self.latency_penalty_bps


def evaluate_sign_strategy(y_true: list[float], y_pred: list[float], *, cost: CostModel) -> dict[str, float]:
    if len(y_true) != len(y_pred):
        raise ValueError('length mismatch')
    if not y_true:
        return {'gross_return': 0.0, 'net_return': 0.0, 'cost_paid': 0.0, 'turnover': 0.0, 'trade_count': 0.0, 'buy_hold_return': 0.0, 'excess_return': 0.0, 'sharpe': 0.0, 'hit_rate': 0.0}
    positions = [1 if p >= 0 else -1 for p in y_pred]
    strat = [pos * ret for pos, ret in zip(positions, y_true)]
    turnover = sum(abs(positions[i] - positions[i-1]) / 2 for i in range(1, len(positions)))
    cost_paid = turnover * cost.total_bps / 10000.0
    gross = sum(strat)
    net = gross - cost_paid
    vol = pstdev(strat) if len(strat) > 1 else 0.0
    return {
        'gross_return': gross,
        'net_return': net,
        'cost_paid': cost_paid,
        'turnover': turnover,
        'trade_count': turnover,
        'buy_hold_return': sum(y_true),
        'excess_return': net - sum(y_true),
        'sharpe': (mean(strat) / vol * sqrt(52)) if vol > 0 else 0.0,
        'hit_rate': mean([1.0 if r > 0 else 0.0 for r in strat]),
    }


def cost_scenarios(y_true: list[float], y_pred: list[float]) -> dict[str, dict[str, float]]:
    return {
        'zero_cost': evaluate_sign_strategy(y_true, y_pred, cost=CostModel(0,0,0,0)),
        'base_cost': evaluate_sign_strategy(y_true, y_pred, cost=CostModel()),
        'stress_cost': evaluate_sign_strategy(y_true, y_pred, cost=CostModel(2,8,5,2)),
    }
