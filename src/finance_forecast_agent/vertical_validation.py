from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .experiment_protocols import audit_experiment_protocol


@dataclass(frozen=True)
class VerticalPaperAudit:
    paper_id: str
    title: str
    experiment_type: str
    market_scope: str
    source_revision: str
    source_license: str
    data_status: str
    environment_status: str
    paper_repository_delta: list[str]
    blockers: list[str]
    protocol: dict[str, Any]
    held_out: bool = False

    @property
    def strict_verified(self) -> bool:
        return not self.blockers and audit_experiment_protocol(
            self.experiment_type, self.protocol
        ).passed

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "protocol_audit": audit_experiment_protocol(
                self.experiment_type, self.protocol
            ).to_dict(),
            "strict_verified": self.strict_verified,
        }


def write_vertical_validation(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    rows = [
        VerticalPaperAudit(
            paper_id="rsr_2020",
            title="Temporal Relational Ranking for Stock Prediction",
            experiment_type="signal_backtest",
            market_scope="US equities daily, NASDAQ/NYSE",
            source_revision="cfbb01bdf194b81bc5893a1b37aff1c0d0d2a82d",
            source_license="GPL-3.0",
            data_status="official processed snapshot present; pretrained embedding external",
            environment_status="TensorFlow 1.x/Python 3.6 runtime not materialized",
            paper_repository_delta=["pretrained sequential embedding is a separate Google Drive artifact"],
            blockers=["pretrained embedding is not frozen", "legacy TensorFlow environment is not locked"],
            protocol={
                "signal_timestamp": "close_t",
                "execution_timestamp": "close_t_plus_1",
                "holding_period": "one day",
                "position_rule": "top-ranked stocks",
                "rebalance_rule": "daily",
                "transaction_cost_bps": 0.1,
                "slippage_bps": 0.0,
                "shorting_rule": "long-only top-k",
                "corporate_action_policy": "official processed Google Finance data",
                "split_protocol": "chronological fixed train validation test indices",
                "metrics": ["investment_return_ratio", "sharpe_ratio"],
            },
        ),
        VerticalPaperAudit(
            paper_id="opensourceap_2022",
            title="Open Source Cross-Sectional Asset Pricing",
            experiment_type="cross_sectional",
            market_scope="US equities monthly",
            source_revision="8db892442c2c3a3779b0f1eac4370d3655be15a1",
            source_license="repository license requires audit",
            data_status="open derived signals exist; several raw inputs require WRDS",
            environment_status="R pipeline not materialized on this Windows host",
            paper_repository_delta=[],
            blockers=["source license is not machine approved", "WRDS-dependent raw inputs prevent clean strict rebuild"],
            protocol={
                "market": "US equities",
                "universe_rule": "CRSP common stocks",
                "point_in_time_policy": "point-in-time source files",
                "characteristic_lag": "at least one month",
                "missing_value_policy": "signal-specific official rule",
                "normalization_rule": "official signal definition",
                "portfolio_formation": "monthly characteristic sorts",
                "weighting_rule": "equal and value weighted",
                "rebalance_rule": "monthly",
                "inference_protocol": "Newey-West",
                "delisting_return_policy": "include CRSP delisting returns",
            },
            held_out=True,
        ),
        VerticalPaperAudit(
            paper_id="arxiv_1706_10059",
            title="Deep Portfolio Management: A Deep Reinforcement Learning Framework",
            experiment_type="portfolio_rl",
            market_scope="Poloniex crypto, 30-minute bars",
            source_revision="48cc5a4af5edefd298e7801b95b0d4696f5175dd",
            source_license="GPL-3.0",
            data_status="historical exchange database absent; legacy endpoint is not reproducible",
            environment_status="TensorFlow 1.x/tflearn runtime not materialized",
            paper_repository_delta=[
                "repository README says code is several versions ahead of the article",
                "repository README says paper test span was about 30% too short and overlapped asset selection",
            ],
            blockers=[
                "official repository is not protocol-identical to the paper",
                "paper-era market database is not frozen",
                "legacy TensorFlow environment is not locked",
            ],
            protocol={
                "state_spec": "price tensor and previous portfolio weights",
                "action_spec": "long-only simplex portfolio weights including cash",
                "reward_spec": "log portfolio growth net of proportional transaction cost",
                "transition_timing": "weights at t applied to price relatives at t+1",
                "portfolio_constraints": "long-only fully invested",
                "transaction_cost_bps": 25.0,
                "training_seeds": [0],
                "evaluation_seeds": [1, 2, 3],
                "baseline_policies": ["UCRP", "Winner", "UBAH"],
                "train_test_protocol": "chronological out-of-sample",
            },
        ),
    ]
    payload = {
        "schema_version": "vertical_validation_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(rows),
        "experiment_type_count": len({row.experiment_type for row in rows}),
        "strict_verified_count": sum(row.strict_verified for row in rows),
        "false_strict_count": 0,
        "papers": [row.to_dict() for row in rows],
        "conclusion": "task protocols pass structurally, but all three paper claims remain blocked by source/data/runtime gates",
    }
    output = project / "reports" / "vertical_validation.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
