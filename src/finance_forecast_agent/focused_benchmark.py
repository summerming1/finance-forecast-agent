"""Policy adapters and reports for the existing Controller, never a second evaluator.

Optuna TPE operates on a frozen finite categorical catalog. Sampling repeats are
reported and rejected before fit; no fallback optimizer is silently substituted.
Every arm uses the same execution/target/seed/resource contracts. A deterministic
or assistant-authored replay run is plumbing evidence, not live Agent quality.
"""

from __future__ import annotations

import copy
import json
import random
import time
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .focused_adaptive import SEARCH_SPACE, EvidenceIndex
from .focused_identity import identity, target_row_ids
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec
from .focused_research import (
    DEFAULT_BASELINES,
    CandidateConfig,
    FocusedResearchAdvisor,
    FocusedResearchController,
    ResearchBudget,
    resolve_feature_columns,
)
from .focused_state import atomic_json

ARMS = ("random", "tpe", "one_shot", "adaptive", "enumerate")


@dataclass(frozen=True)
class BenchmarkSpec:
    candidate_budget: int = 12
    search_seed: int = 42
    estimator_seed: int = 42
    startup_trials: int = 4
    max_sampler_draws: int = 512
    schema_version: str = "focused_benchmark_contract_v2"

    def __post_init__(self):
        for key in ("candidate_budget", "startup_trials", "max_sampler_draws"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        for key in ("search_seed", "estimator_seed"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**32 - 1:
                raise ValueError(f"{key} must be a non-negative 32-bit integer")
        if self.candidate_budget > 100:
            raise ValueError("bounded benchmark permits at most 100 candidates")


def catalog_candidate(config: dict, seed: int = 42) -> CandidateConfig:
    if set(config) - {"model_family", "model_params", "feature_groups", "config_identity"}:
        raise ValueError("catalog cannot override task, seed, metrics or evaluation")
    c = CandidateConfig(
        "catalog",
        config["model_family"],
        dict(config.get("model_params", {})),
        list(config["feature_groups"]),
        seed=seed,
    )
    resolve_feature_columns(c.feature_groups)
    _ = c.fingerprint  # validate model, effective params and estimator seed
    if config.get("config_identity") not in {None, c.config_identity}:
        raise ValueError("catalog identity mismatch")
    return c


def validate_catalog(configs: list[dict]) -> list[dict]:
    if not 1 <= len(configs) <= 200:
        raise ValueError("frozen catalog size must be in [1,200]")
    rows, seen = [], set()
    for config in configs:
        candidate = catalog_candidate(config)
        if candidate.config_identity in seen:
            raise ValueError("duplicate effective configuration in catalog")
        seen.add(candidate.config_identity)
        rows.append(
            {
                "model_family": candidate.model_family,
                "model_params": candidate.model_params,
                "feature_groups": sorted(set(candidate.feature_groups)),
                "config_identity": candidate.config_identity,
            }
        )
    return rows


def default_catalog() -> list[dict]:
    # Full approved model families, no new models or target semantics. Small
    # catalog remains available for exhaustive correctness checks.
    rows = [copy.deepcopy(row) for row in SEARCH_SPACE]
    for alpha in (0.1, 0.5, 2.0, 5.0, 20.0, 100.0):
        for groups in (["base_lags"], ["base_lags", "momentum"], ["base_lags", "volatility"]):
            row = {"model_family": "ridge_regression", "model_params": {"alpha": alpha}, "feature_groups": groups}
            if catalog_candidate(row).config_identity not in {catalog_candidate(x).config_identity for x in rows}:
                rows.append(row)
    for family, params, extra in (
        ("random_forest_regressor", {"max_depth": 4, "min_samples_leaf": 8}, "volatility"),
        ("gradient_boosting_regressor", {"learning_rate": 0.03, "max_depth": 2}, "momentum"),
    ):
        for trees in (100, 50, 25, 12, 10):
            for groups in (["base_lags"], ["base_lags", extra]):
                row = {
                    "model_family": family,
                    "model_params": {**params, "n_estimators": trees},
                    "feature_groups": groups,
                }
                if catalog_candidate(row).config_identity not in {catalog_candidate(x).config_identity for x in rows}:
                    rows.append(row)
    return validate_catalog(rows)


class BenchmarkAdvisor:
    """Only proposes decisions. All training/validation belongs to Controller."""

    def __init__(self, native: FocusedResearchAdvisor, config: dict):
        self.native = native
        self.mode, self.fixture_dir, self.replay_call_ids = native.mode, native.fixture_dir, native.replay_call_ids
        self.config = copy.deepcopy(config)
        self.arm = config["arm"]
        if self.arm not in ARMS:
            raise ValueError("unsupported benchmark arm")
        self.spec = BenchmarkSpec(**config["spec"])
        self.catalog = validate_catalog(config["catalog"])
        if self.spec.candidate_budget > len(self.catalog):
            raise ValueError("candidate budget exceeds unique catalog size")
        self.last_record = None
        self.last_fixture_path = None
        self.last_telemetry = {}
        self.runtime = None
        self.contract = {
            **config,
            "catalog": self.catalog,
            "implementation": "optuna.samplers.TPESampler"
            if self.arm == "tpe"
            else "FocusedResearchAdvisor"
            if self.arm in {"one_shot", "adaptive"}
            else self.arm,
            "optuna_version": version("optuna") if self.arm == "tpe" else None,
            "tpe_search_representation": "categorical_config_identity",
            "sampler_rng_policy": "search_seed + decision_index modulo 2**32",
        }

    def prepare_prompt(self, prompt: dict, runtime) -> dict:
        self.runtime = runtime
        body = copy.deepcopy(prompt)
        with runtime.db.transaction() as db:
            attempts = db.execute(
                "SELECT * FROM attempts WHERE ns=? AND role='research_candidate' ORDER BY rowid", (runtime.ns,)
            ).fetchall()
        body["executed_candidates"] = [
            {"candidate": json.loads(row["payload"])["candidate"], "status": row["status"]} for row in attempts
        ]
        body["search_catalog"] = copy.deepcopy(self.catalog)
        body["strategy_context"] = {
            "arm": self.arm,
            "candidate_budget": self.spec.candidate_budget,
            "estimator_seed": self.spec.estimator_seed,
            "planning_mode": "one_shot_frozen_batch" if self.arm == "one_shot" else "feedback_driven",
        }
        body["rules"] += [
            "Training candidates must match exactly one search_catalog configuration and estimator_seed.",
            "Do not propose a new task, metric or new feature outside the frozen catalog.",
        ]
        if self.arm == "one_shot":
            body["max_hypotheses"] = self.spec.candidate_budget
            body["rules"].append("Propose the whole bounded plan now. No intermediate feedback will be provided.")
        else:
            body["max_hypotheses"] = 1
        return body

    def validate_compiled(self, compiled):
        ids = {row["config_identity"] for row in self.catalog}
        for _, candidate in compiled:
            if candidate is not None and (
                candidate.config_identity not in ids or candidate.seed != self.spec.estimator_seed
            ):
                raise ValueError("candidate is outside frozen benchmark catalog/estimator seed")

    def propose(self, prompt: dict) -> tuple[dict, str]:
        self.last_record, self.last_fixture_path = None, None
        self.last_telemetry = {"sampler_draws": 0, "sampler_duplicate_rejections": 0, "tpe_model_based": False}
        used = {row["candidate"]["config_identity"] for row in prompt["executed_candidates"]}
        used |= {row["config_identity"] for row in prompt["baseline_results"]}
        remaining = [row for row in self.catalog if row["config_identity"] not in used]
        completed_count = len(prompt["executed_candidates"])
        if completed_count >= self.spec.candidate_budget or not remaining:
            return {
                "hypotheses": [{"action_type": "stop", "statement": "Frozen candidate budget or catalog exhausted."}]
            }, "benchmark_stop"
        if self.arm == "one_shot" and prompt["round_index"] > 1:
            return {
                "hypotheses": [
                    {"action_type": "stop", "statement": "One-shot frozen plan completed; no feedback replanning."}
                ]
            }, "one_shot_plan_complete"
        if self.arm in {"one_shot", "adaptive"}:
            started = time.monotonic()
            self.last_telemetry["provider_attempted"] = self.mode == "live"
            try:
                return self.native.propose(prompt)
            finally:
                self.last_record, self.last_fixture_path = self.native.last_record, self.native.last_fixture_path
                self.last_telemetry["advisor_seconds"] = time.monotonic() - started
        if self.arm == "random":
            order = list(self.catalog)
            random.Random(self.spec.search_seed).shuffle(order)
            config = next(row for row in order if row["config_identity"] not in used)
        elif self.arm == "enumerate":
            config = remaining[0]
        else:
            config = self._tpe(prompt, used)
            if config is None:
                return {
                    "hypotheses": [
                        {"action_type": "stop", "statement": "TPE duplicate-draw bound exhausted; no fallback."}
                    ]
                }, "tpe_sampling_stalled"
        return {
            "hypotheses": [
                {
                    "action_type": "improve",
                    "statement": f"{self.arm} proposal under frozen search contract",
                    "model_family": config["model_family"],
                    "model_params": config["model_params"],
                    "feature_groups": config["feature_groups"],
                    "seed": self.spec.estimator_seed,
                    "parent_candidate_id": "baseline_ridge",
                    "evidence_refs": ["baseline_ridge"],
                }
            ]
        }, f"{self.arm}_policy"

    def _tpe(self, prompt, used):
        import optuna
        from optuna.distributions import CategoricalDistribution
        from optuna.trial import TrialState, create_trial

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        ids = [row["config_identity"] for row in self.catalog]
        distributions = {"config": CategoricalDistribution(ids)}
        sampler = optuna.samplers.TPESampler(
            seed=(self.spec.search_seed + prompt["round_index"]) % 2**32,
            n_startup_trials=self.spec.startup_trials,
            multivariate=False,
            constant_liar=False,
        )
        study = optuna.create_study(direction="minimize", sampler=sampler)
        successful = {row["candidate_id"]: row for row in prompt["prior_research_results"]}
        n_complete = 0
        for attempt in prompt["executed_candidates"]:
            c = attempt["candidate"]
            if c["config_identity"] not in ids:
                raise ValueError("observed candidate not in frozen TPE space")
            result = successful.get(c["candidate_id"]) if attempt["status"] == "completed" else None
            state = TrialState.COMPLETE if result else TrialState.FAIL
            study.add_trial(
                create_trial(
                    params={"config": c["config_identity"]},
                    distributions=distributions,
                    state=state,
                    value=float(result["metrics"]["mae"]) if result else None,
                )
            )
            n_complete += result is not None
        self.last_telemetry["tpe_model_based"] = n_complete >= self.spec.startup_trials
        # Bounded rejection, not hidden resampling with free model fits.
        for _ in range(self.spec.max_sampler_draws):
            trial = study.ask()
            choice = trial.suggest_categorical("config", ids)
            self.last_telemetry["sampler_draws"] += 1
            if choice not in used:
                return self.catalog[ids.index(choice)]
            study.tell(trial, state=TrialState.PRUNED)
            self.last_telemetry["sampler_duplicate_rejections"] += 1
        return None


def _report(controller, *, error: Exception | None, elapsed: float, comparison_contract: dict, algorithm: dict) -> dict:
    runtime = controller._runtime
    if runtime is None:
        raise RuntimeError("benchmark preflight failed before runtime creation") from error
    with runtime.db.transaction() as db:
        attempts = [
            dict(row)
            for row in db.execute("SELECT * FROM attempts WHERE ns=? ORDER BY rowid", (runtime.ns,)).fetchall()
        ]
        objects = {
            row["key"]: json.loads(row["payload"])
            for row in db.execute("SELECT key,payload FROM objects WHERE ns=?", (runtime.ns,)).fetchall()
        }
        events = [
            json.loads(row[0])
            for row in db.execute("SELECT payload FROM events WHERE ns=? ORDER BY id", (runtime.ns,)).fetchall()
        ]
    comparison_contract = {
        **comparison_contract,
        "source": runtime.contract["source"],
        "environment": runtime.contract["environment"],
        "provider": runtime.contract["provider"],
        "advisor_mode": controller.advisor.mode,
    }
    results = [(obj["row"].get("result") or obj["row"]) for key, obj in objects.items() if key.startswith("result:")]
    baseline_ids = {row[0] for row in DEFAULT_BASELINES} | {"baseline_zero", "baseline_mean", "baseline_median"}
    baselines = [row for row in results if row["candidate"]["candidate_id"] in baseline_ids]
    candidates = [row for row in results if row["candidate"]["candidate_id"] not in baseline_ids]
    best = min([*baselines, *candidates], key=lambda row: row["metrics"]["mae"]) if results else None
    baseline = min(baselines, key=lambda row: row["metrics"]["mae"]) if baselines else None
    target_contracts = set()
    for row in results:
        accepted = runtime.accepted(row["candidate"]["candidate_id"])
        artifact_ref = row.get("prediction_artifact_ref")
        if not artifact_ref:
            artifact_ref = next(
                x["path"]
                for x in accepted["artifacts"]
                if "/predictions/" in x["path"] or x["path"].startswith("predictions/")
            )
        artifact = json.loads((runtime.root / artifact_ref).read_text())
        keys = [(r["fold_id"], r["row_id"]) for r in artifact["rows"]]
        target_contracts.add(identity(keys, domain="benchmark-evaluation-targets-v1"))
    if len(target_contracts) > 1:
        raise ValueError("benchmark compared candidates on different target rows")
    calls = [value for key, value in objects.items() if key.startswith("advisor_attempt:")]
    records = [x["call_record"] for x in calls if x.get("call_record")]
    live = [x for x in records if x.get("created_by") == "live_provider_record" and controller.advisor.mode == "live"]
    replay = [x for x in records if controller.advisor.mode == "replay"]
    provider_attempts = sum(bool(x.get("telemetry", {}).get("provider_attempted")) for x in calls)
    provider_costs = [x.get("provider_metadata", {}).get("cost") for x in live]
    # Unknown cost is null, never zero. Pricing must be externally supplied.
    cost = (
        sum(provider_costs)
        if provider_costs
        and len(provider_costs) == provider_attempts
        and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x) and x >= 0
            for x in provider_costs
        )
        else (0 if not provider_attempts else None)
    )
    unique = {
        json.loads(a["payload"])["candidate"]["config_identity"] for a in attempts if a["role"] == "research_candidate"
    }
    decisions = [x for x in calls if x.get("telemetry")]
    final = objects.get("final") or objects.get("pause") or {}
    round_items = [item for key, obj in objects.items() if key.startswith("round:") for item in obj["items"]]
    report = {
        "schema_version": "focused_benchmark_arm_v2",
        "arm": algorithm["arm"],
        "algorithm": algorithm,
        "comparison_contract": comparison_contract,
        "comparison_contract_hash": identity(comparison_contract, domain="benchmark-comparison-v2"),
        "comparison_target_hash": next(iter(target_contracts), None),
        "comparison_target_count": best.get("prediction_count", 0) if best else 0,
        "campaign_id": controller.spec.campaign_id,
        "campaign_dir": str(runtime.root),
        "execution_contract_hash": runtime.contract_hash,
        "execution_status": "failed" if error else final.get("execution_status", "partial"),
        "research_outcome": final.get("research_outcome", "inconclusive"),
        "stop_reason": final.get("stop_reason"),
        "error_type": type(error).__name__ if error else None,
        "best": best,
        "baseline": baseline,
        "results": candidates,
        "relative_mae_improvement": ((baseline["metrics"]["mae"] - best["metrics"]["mae"]) / baseline["metrics"]["mae"])
        if best and baseline
        else None,
        "fold_stability": {
            "mae_by_fold": [x["mae"] for x in best["fold_metrics"]],
            "mae_std": float(np.std([x["mae"] for x in best["fold_metrics"]])),
        }
        if best
        else None,
        "telemetry": {
            **runtime.resource_usage(),
            "unique_candidates": len(unique),
            "candidate_charged_fits": sum(a["reserved"] for a in attempts if a["role"] == "research_candidate"),
            "candidate_failed_attempts": sum(
                a["status"] == "failed" and a["role"] == "research_candidate" for a in attempts
            ),
            "invalid_proposals": sum(
                e.get("type") == "proposal.rejected" or e.get("event_type") == "proposal.rejected" for e in events
            ),
            "duplicate_proposals": sum(x["status"] == "skipped_duplicate" for x in round_items),
            "negative_experiments": sum(
                x.get("research_verdict") == "development_screen_not_passed" for x in candidates
            ),
            "llm_calls": len(live),
            "provider_attempts": provider_attempts,
            "provider_attempts_without_record": max(0, provider_attempts - len(live)),
            "replay_calls": len(replay),
            "advisor_reservations": objects.get("advisor_call_reservations", 0),
            "provider_usage": [r.get("provider_metadata", {}).get("usage") for r in live],
            "llm_cost": cost,
            "sampler_draws": sum(x["telemetry"].get("sampler_draws", 0) for x in decisions),
            "sampler_duplicate_rejections": sum(
                x["telemetry"].get("sampler_duplicate_rejections", 0) for x in decisions
            ),
            "tpe_model_based_decisions": sum(bool(x["telemetry"].get("tpe_model_based")) for x in decisions),
            "wall_seconds": elapsed,
            "wall_scope": "this invocation; resumed runs do not reconstruct past process downtime",
            "advisor_seconds_total": sum(x.get("elapsed_seconds", 0) for x in calls),
            "human_minutes": None,
        },
        "live_quality_evidence": bool(live) and error is None,
        "evidence_level": (
            "simulation_only" if controller.dataset.exposure == "simulation_only" else "development_only"
        ),
        "memory_mode": "warm" if controller.use_memory_prior else "cold",
        "limitations": [
            "Finite catalog comparison; overlapping windows and deterministic repeats are not independent samples.",
            "Synthetic/replay/control results are not live LLM or financial quality evidence.",
            "No automatic superiority verdict; human-operation time must be measured separately.",
        ],
    }
    atomic_json(controller.project_dir / "benchmark_arm.json", report)
    return report


def run_benchmark_arm(
    frame,
    dataset,
    *,
    project_dir: str | Path,
    arm: str,
    spec: BenchmarkSpec,
    split_spec: FocusedSplitSpec | None = None,
    catalog: list[dict] | None = None,
    llm_mode: str = "deterministic",
    fixture_dir: str | Path | None = None,
    replay_call_ids: dict | None = None,
    reviewed_evidence: list[dict] | None = None,
    resume_existing: bool = False,
    use_memory_prior: bool = False,
    memory_store_path: str | Path | None = None,
    state_path: str | Path | None = None,
) -> dict:
    split = split_spec or FocusedSplitSpec()
    catalog = validate_catalog(catalog or default_catalog())
    budget = ResearchBudget(
        max_rounds=2 * spec.candidate_budget + 1,
        max_new_candidates_per_round=spec.candidate_budget,
        max_fit_calls=split.baseline_fit_calls(len(DEFAULT_BASELINES)) + spec.candidate_budget * split.max_folds,
        max_advisor_calls=2 * spec.candidate_budget + 1,
    )
    config = {"arm": arm, "spec": asdict(spec), "catalog": catalog}
    from .focused_data import FocusedTaskSpec

    task = FocusedTaskSpec()
    target_keys = target_row_ids(frame, task.to_dict())
    eval_keys = [target_keys[int(i)] for _, test in split.build_splits(len(frame)) for i in test]
    comparison = {
        "spec": asdict(spec),
        "catalog": catalog,
        "task": task.to_dict(),
        "frame": dataset.frame_fingerprint,
        "target_rows": eval_keys,
        "split": split.to_dict(),
        "evaluation": EvaluationPolicy().to_dict(),
        "budget": budget.to_dict(),
        "reviewed_evidence": EvidenceIndex(reviewed_evidence or []).rows,
        "memory_mode": "warm" if use_memory_prior else "cold",
    }
    campaign_id = (
        "benchmark-"
        + identity(
            {
                "strategy": config,
                "frame": dataset.frame_fingerprint,
                "mode": llm_mode,
                "project": str(Path(project_dir).resolve()),
                "memory": use_memory_prior,
            },
            domain="benchmark-arm-v2",
        )[:20]
    )
    memory_snapshot = []
    if use_memory_prior:
        from .experiment_memory import ExperimentMemoryStore
        from .focused_delivery import load_focused_memory_evidence

        memory_snapshot = load_focused_memory_evidence(
            ExperimentMemoryStore(memory_store_path or Path(project_dir) / "experiment_memory.json"),
            tenant_id="default",
            task=task,
            dataset_fingerprint=dataset.semantic_fingerprint,
            split_spec=split,
            evaluation_policy=EvaluationPolicy(),
            exclude_campaign_id=campaign_id,
        )
    comparison["memory_snapshot_hash"] = identity(memory_snapshot, domain="benchmark-memory-snapshot")
    controller = FocusedResearchController(
        project_dir=project_dir,
        frame=frame,
        task=task,
        dataset=dataset,
        budget=budget,
        split_spec=split,
        advisor_mode=llm_mode,
        fixture_dir=fixture_dir,
        replay_call_ids=replay_call_ids,
        reviewed_evidence=reviewed_evidence,
        use_memory_prior=use_memory_prior,
        memory_store_path=memory_store_path,
        campaign_id=campaign_id,
        resume_existing=resume_existing,
        benchmark_strategy=config,
        state_path=state_path,
    )
    started, error = time.monotonic(), None
    try:
        controller.run()
    except (ValueError, TypeError, RuntimeError, OSError) as exc:
        error = exc
    return _report(
        controller,
        error=error,
        elapsed=time.monotonic() - started,
        comparison_contract=comparison,
        algorithm=controller.advisor.contract,
    )


def benchmark_summary(arms: list[dict]) -> dict:
    if not arms or len({x["arm"] for x in arms}) != len(arms):
        raise ValueError("benchmark arms must be nonempty and unique")
    if len({x["comparison_contract_hash"] for x in arms}) != 1:
        raise ValueError("benchmark arms have different comparison contracts")
    if len({x["comparison_target_hash"] for x in arms if x["comparison_target_hash"]}) > 1:
        raise ValueError("benchmark arms have different comparison target identities")
    paired = []
    for left in arms:
        for right in arms:
            if left["arm"] < right["arm"] and left["best"] and right["best"]:
                paired.append(
                    {
                        "left": left["arm"],
                        "right": right["arm"],
                        "mae_delta": left["best"]["metrics"]["mae"] - right["best"]["metrics"]["mae"],
                    }
                )
    return {
        "schema_version": "focused_agent_value_benchmark_v2",
        "arms": arms,
        "paired_comparisons": paired,
        "agent_superiority_claim": False,
        "comparison_contract_hash": arms[0]["comparison_contract_hash"],
        "engineering_complete": all(a["execution_status"] == "completed" for a in arms),
        "live_llm_quality_complete": all(
            a["live_quality_evidence"] for a in arms if a["arm"] in {"one_shot", "adaptive"}
        )
        and {"one_shot", "adaptive"} <= {a["arm"] for a in arms},
        "warning": "No pooling across overlapping windows or counting deterministic repeats as independent trials.",
    }
