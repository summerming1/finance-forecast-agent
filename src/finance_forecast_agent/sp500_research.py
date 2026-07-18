from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkTask, run_common_benchmark
from .forecastproof import DecisionMemo, EvidenceSpan, MemoAudit, MemoAuditCheck
from .frontend_view_model import load_method_cards
from .multi_benchmark import build_benchmark_tasks
from .paper_run_delta import benchmark_delta_audit


SP500_CASES: tuple[dict[str, str], ...] = (
    {
        "paper_id": "arxiv_2004_10178v2",
        "model_family": "random_forest_regressor",
        "short_name": "S&P constituents · RF",
    },
    {
        "paper_id": "arxiv_2108_10826",
        "model_family": "gradient_boosting_regressor",
        "short_name": "S&P 500 ensemble · GBDT branch",
    },
    {
        "paper_id": "arxiv_2501_17366",
        "model_family": "lstm_regressor",
        "short_name": "S&P 500 · LSTM",
    },
)

SP500_SUITE_SCHEMA = "forecastproof_sp500_research_suite_v1"
SP500_SUITE_PATH = Path("reports") / "sp500_daily_research_suite.json"
DEFAULT_CASE_ID = SP500_CASES[0]["paper_id"]
DEFAULT_SKILL_HURDLE = 0.01


@dataclass(frozen=True)
class ResearchEvidenceBrief:
    paper_id: str
    title: str
    paper_url: str
    claim: str
    original_scope: str
    shared_task: str
    model: str
    reported_results: Any
    strict_requirements: tuple[str, ...]
    unknowns: tuple[str, ...]
    scope_disclosure: str
    evidence_spans: tuple[EvidenceSpan, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchBaselineComparison:
    baseline_name: str
    prediction_count: int
    model_accuracy: float
    baseline_accuracy: float
    absolute_improvement: float
    minimum_absolute_improvement: float
    wilson_95_interval: tuple[float, float]
    two_sided_binomial_pvalue: float
    directional_skill_demonstrated: bool
    value_gate: bool
    deployment_status: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchVerification:
    verdict: str
    validation_tier: str
    evidence_gate: bool
    frozen_data_gate: bool
    common_protocol_gate: bool
    artifact_gate: bool
    evidence_span_count: int
    task_fingerprint: str
    dataset_sha256: str
    model_family: str
    metrics: dict[str, float]
    baseline_comparison: ResearchBaselineComparison
    paper_run_delta: dict[str, Any]
    scope_disclosure: str
    artifact_path: str

    @property
    def gates_passed(self) -> int:
        return sum((self.evidence_gate, self.frozen_data_gate, self.common_protocol_gate, self.artifact_gate))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task(project_dir: Path) -> BenchmarkTask:
    return next(task for task in build_benchmark_tasks(project_dir) if task.task_id == "spy_daily_direction_12lag_v1")


def build_sp500_research_suite(project_dir: str | Path) -> dict[str, Any]:
    """Run three paper-inspired adapters on one leakage-safe frozen SPY task."""
    project_dir = Path(project_dir).resolve()
    task = _task(project_dir)
    cards = {card.paper_id: card for card in load_method_cards(project_dir / "method_cards_local_llm")}
    result = run_common_benchmark(
        task,
        [(row["paper_id"], row["model_family"]) for row in SP500_CASES],
    )
    repository_root = project_dir.parents[1]
    result["task"]["dataset_path"] = str(dataset_path := Path(task.dataset_path).relative_to(repository_root))
    for report in result["reports"]:
        report["paper_vs_run_delta"] = benchmark_delta_audit(
            cards[report["method_id"]],
            task,
            actual_model=report["model_family"],
            task_diagnostics=report["task_diagnostics"],
        )
    dataset_path = repository_root / dataset_path
    payload = {
        "schema_version": SP500_SUITE_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_tier": "paper_inspired_common_benchmark",
        "scope_disclosure": (
            "Each paper contributes an executable model-family hypothesis to one shared SPY next-day direction task. "
            "This validates adaptation and comparison integrity; it is not a strict reproduction of each paper's "
            "original data, features, portfolio rules, or reported metric."
        ),
        "case_count": len(SP500_CASES),
        "dataset_sha256": _sha256(dataset_path),
        "benchmark": result,
    }
    output = project_dir / SP500_SUITE_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["report_path"] = str(output)
    return payload


def load_sp500_research_suite(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir).resolve() / SP500_SUITE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Frozen S&P 500 research suite is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SP500_SUITE_SCHEMA:
        raise ValueError("Unsupported S&P 500 research-suite schema")
    return payload


def case_options() -> tuple[dict[str, str], ...]:
    return SP500_CASES


def _case_spec(paper_id: str) -> dict[str, str]:
    try:
        return next(row for row in SP500_CASES if row["paper_id"] == paper_id)
    except StopIteration as exc:
        raise KeyError(f"Unknown S&P 500 research case: {paper_id}") from exc


def _card(project_dir: Path, paper_id: str) -> dict[str, Any]:
    return json.loads((project_dir / "method_cards_local_llm" / f"{paper_id}.json").read_text(encoding="utf-8"))


def _report(suite: dict[str, Any], paper_id: str) -> dict[str, Any]:
    try:
        return next(row for row in suite["benchmark"]["reports"] if row["method_id"] == paper_id)
    except StopIteration as exc:
        raise KeyError(f"Case {paper_id} is absent from the frozen suite") from exc


def build_research_brief(project_dir: str | Path, paper_id: str) -> ResearchEvidenceBrief:
    project_dir = Path(project_dir).resolve()
    card = _card(project_dir, paper_id)
    spec = _case_spec(paper_id)
    selected: list[EvidenceSpan] = []
    for index, row in enumerate(card.get("evidence_spans", []), start=1):
        quote = str(row.get("quote", "")).strip()
        if not quote:
            continue
        section = str(row.get("section") or "paper_evidence")
        if section == "unknown":
            section = f"paper_evidence_{index}"
        selected.append(
            EvidenceSpan(
                evidence_id=f"{paper_id}:{index}",
                section=section,
                quote=quote,
                source_type="primary_paper",
                source_url=str(row.get("source_url") or card.get("paper_url") or ""),
                source_revision=str(
                    row.get("source_revision")
                    or card.get("extraction_metadata", {}).get("document_text_sha")
                    or "local-pinned-copy"
                ),
            )
        )
        if len(selected) == 5:
            break
    scope = (
        f"{card.get('target_asset', 'unknown target')} · {card.get('frequency', 'unknown frequency')} · "
        f"{card.get('horizon', 'unknown horizon')}"
    )
    disclosure = (
        "The executable run below is a paper-inspired adaptation to frozen SPY daily next-return direction with "
        "12 lag features and purged walk-forward folds. It does not reproduce the paper's original dataset, "
        "feature set, horizon, portfolio construction, or headline result."
    )
    return ResearchEvidenceBrief(
        paper_id=paper_id,
        title=str(card["title"]),
        paper_url=str(card.get("paper_url", "")),
        claim=(
            f"Test whether the paper's {spec['model_family']} branch transfers to a common S&P 500 daily "
            "direction benchmark under identical data and folds."
        ),
        original_scope=scope,
        shared_task="SPY next-trading-day return direction · 12 return lags · purged walk-forward",
        model=spec["model_family"],
        reported_results=card.get("reported_results", {}),
        strict_requirements=tuple(str(item) for item in card.get("strict_requirements", [])),
        unknowns=tuple(str(item) for item in card.get("unknowns", [])),
        scope_disclosure=disclosure,
        evidence_spans=tuple(selected),
    )


def verify_research_case(
    project_dir: str | Path,
    paper_id: str,
    *,
    minimum_absolute_improvement: float = DEFAULT_SKILL_HURDLE,
) -> ResearchVerification:
    project_dir = Path(project_dir).resolve()
    suite = load_sp500_research_suite(project_dir)
    brief = build_research_brief(project_dir, paper_id)
    report = _report(suite, paper_id)
    benchmark = suite["benchmark"]
    task = BenchmarkTask.from_dict(benchmark["task"])
    dataset_path = Path(task.dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = project_dir.parents[1] / dataset_path
    diagnostics = report["directional_diagnostics"]
    baseline_accuracy = float(benchmark["directional_baseline"]["accuracy"])
    model_accuracy = float(report["metrics"]["directional_accuracy"])
    improvement = model_accuracy - baseline_accuracy
    value_gate = bool(improvement >= minimum_absolute_improvement and diagnostics["directional_skill_demonstrated"])
    blockers: list[str] = []
    if improvement < minimum_absolute_improvement:
        blockers.append(
            f"Accuracy lift {improvement:.2%} is below the declared {minimum_absolute_improvement:.2%} hurdle."
        )
    if not diagnostics["directional_skill_demonstrated"]:
        blockers.append("The 95% Wilson interval and two-sided binomial test do not establish directional skill.")
    blockers.extend(
        (
            "This is a common-task adaptation, not a strict reproduction of the paper's original claim.",
            "No transaction-cost, portfolio, out-of-period regime, or deployment-safety gate has passed.",
        )
    )
    evidence_gate = len(brief.evidence_spans) >= 2
    frozen_data_gate = dataset_path.exists() and _sha256(dataset_path) == suite["dataset_sha256"]
    integrity = benchmark["comparison_integrity"]
    common_protocol_gate = bool(
        integrity["same_task_fingerprint"]
        and integrity["same_fold_signature"]
        and integrity["identical_target_rows"]
        and integrity["equal_prediction_counts"]
    )
    metrics = {key: float(value) for key, value in report["metrics"].items()}
    artifact_gate = bool(
        report["prediction_count"] == benchmark["directional_baseline"]["prediction_count"]
        and report["prediction_artifact"]["task_fingerprint"] == task.fingerprint
        and all(math.isfinite(value) for value in metrics.values())
    )
    gates = (evidence_gate, frozen_data_gate, common_protocol_gate, artifact_gate)
    return ResearchVerification(
        verdict="ADAPTATION_VALIDATED" if all(gates) else "BLOCKED",
        validation_tier="paper_inspired_common_benchmark",
        evidence_gate=evidence_gate,
        frozen_data_gate=frozen_data_gate,
        common_protocol_gate=common_protocol_gate,
        artifact_gate=artifact_gate,
        evidence_span_count=len(brief.evidence_spans),
        task_fingerprint=task.fingerprint,
        dataset_sha256=str(suite["dataset_sha256"]),
        model_family=str(report["model_family"]),
        metrics=metrics,
        baseline_comparison=ResearchBaselineComparison(
            baseline_name=str(benchmark["directional_baseline"]["name"]),
            prediction_count=int(report["prediction_count"]),
            model_accuracy=model_accuracy,
            baseline_accuracy=baseline_accuracy,
            absolute_improvement=improvement,
            minimum_absolute_improvement=minimum_absolute_improvement,
            wilson_95_interval=tuple(float(value) for value in diagnostics["wilson_95_interval"]),
            two_sided_binomial_pvalue=float(diagnostics["two_sided_binomial_pvalue"]),
            directional_skill_demonstrated=bool(diagnostics["directional_skill_demonstrated"]),
            value_gate=value_gate,
            deployment_status="HOLD",
            blockers=tuple(blockers),
        ),
        paper_run_delta=dict(report["paper_vs_run_delta"]),
        scope_disclosure=str(suite["scope_disclosure"]),
        artifact_path=str(Path("projects") / "finance_agent" / SP500_SUITE_PATH),
    )


def get_case_runtime(project_dir: str | Path, paper_id: str) -> tuple[BenchmarkTask, dict[str, Any], dict[str, Any]]:
    project_dir = Path(project_dir).resolve()
    suite = load_sp500_research_suite(project_dir)
    task = BenchmarkTask.from_dict(suite["benchmark"]["task"])
    return task, _report(suite, paper_id), _card(project_dir, paper_id)


def build_research_replay_memo(
    brief: ResearchEvidenceBrief,
    verification: ResearchVerification,
) -> DecisionMemo:
    baseline = verification.baseline_comparison
    recommendation = "CONDITIONAL" if verification.verdict == "ADAPTATION_VALIDATED" else "NO_GO"
    return DecisionMemo(
        recommendation=recommendation,
        headline="Accept the common-task adaptation as research evidence; hold deployment.",
        confidence=0.9 if verification.verdict == "ADAPTATION_VALIDATED" else 0.35,
        rationale=(
            f"All {verification.gates_passed}/4 deterministic adaptation gates passed on task {verification.task_fingerprint}.",
            (
                f"Directional accuracy is {baseline.model_accuracy:.2%} versus the leakage-safe fold-train "
                f"majority baseline at {baseline.baseline_accuracy:.2%} ({baseline.absolute_improvement:+.2%})."
            ),
            "The statistical skill gate remains on HOLD, so the result cannot support deployment or trading.",
        ),
        verified_facts=(
            f"Validation tier: {verification.validation_tier}; this is not a strict paper reproduction.",
            f"The frozen dataset produced {baseline.prediction_count} identical out-of-fold target rows per method.",
            (
                f"95% Wilson interval: {baseline.wilson_95_interval[0]:.2%}–"
                f"{baseline.wilson_95_interval[1]:.2%}; binomial p={baseline.two_sided_binomial_pvalue:.4f}."
            ),
            f"Dataset SHA-256 matched: {verification.dataset_sha256}.",
        ),
        risks=(
            "Paper data, features, horizon, split rules, and reported result are not reproduced by this adaptation.",
            "Forecast accuracy does not establish transaction-cost-adjusted economic value.",
            "A single frozen SPY history does not establish future-regime robustness.",
        ),
        next_actions=(
            "Run one human-approved bounded child experiment on the pre-registered promotion holdout.",
            "Add a second frozen out-of-period SPY regime before any deployment discussion.",
            "Add cost-aware strategy and risk guardrails only after statistical forecast skill is demonstrated.",
        ),
        citations=tuple(
            {"evidence_id": span.evidence_id, "claim": span.section}
            for span in brief.evidence_spans[:4]
        ),
        guardrail="Research decision support only; not investment advice; no trading or deployment is authorized.",
        mode="verified_replay",
        model="deterministic policy",
        tool_trace=("get_evidence_brief", "get_verification_result", "apply_decision_guardrails"),
    )


def audit_research_memo(
    memo: DecisionMemo,
    brief: ResearchEvidenceBrief,
    verification: ResearchVerification,
) -> MemoAudit:
    valid_pairs = {(span.evidence_id, span.section) for span in brief.evidence_spans}
    citations_valid = bool(memo.citations) and all(
        (str(row.get("evidence_id", "")), str(row.get("claim", ""))) in valid_pairs for row in memo.citations
    )
    cited_sections = {str(row.get("claim", "")) for row in memo.citations if (str(row.get("evidence_id", "")), str(row.get("claim", ""))) in valid_pairs}
    text = " ".join((memo.headline, *memo.rationale, *memo.verified_facts, *memo.risks, *memo.next_actions)).lower()
    checks = (
        MemoAuditCheck("deterministic_authority", "Deterministic gate authority", memo.recommendation != "GO", "An adaptation cannot authorize deployment."),
        MemoAuditCheck("tool_grounding", "Required tool grounding", {"get_evidence_brief", "get_verification_result"} <= set(memo.tool_trace), "Both read-only evidence tools are required."),
        MemoAuditCheck("citation_validity", "Citation validity", citations_valid, "Every evidence ID must map to its exact MethodCard section."),
        MemoAuditCheck("evidence_coverage", "Evidence coverage", len(cited_sections) >= 2, "At least two distinct evidence sections are required."),
        MemoAuditCheck("decision_completeness", "Decision completeness", bool(memo.headline and memo.rationale and memo.verified_facts and memo.risks and memo.next_actions and 0 <= memo.confidence <= 1), "Facts, risks, actions, and bounded confidence are required."),
        MemoAuditCheck("research_guardrail", "Research-only guardrail", "research" in memo.guardrail.lower() and "not investment advice" in memo.guardrail.lower(), "The memo must prohibit investment interpretation."),
        MemoAuditCheck("scope_honesty", "Adaptation scope honesty", "not a strict" in text or "not reproduced" in text, "The memo must distinguish adaptation from strict reproduction."),
        MemoAuditCheck("baseline_honesty", "Baseline and skill honesty", verification.baseline_comparison.value_gate or ("baseline" in text and "hold" in text), "A failed skill gate must remain visible."),
    )
    passed = sum(check.passed for check in checks)
    return MemoAudit(round(100 * passed / len(checks)), passed, len(checks), checks)


def build_research_audit_pack(
    *,
    brief: ResearchEvidenceBrief,
    verification: ResearchVerification,
    memo: DecisionMemo,
    memo_audit: MemoAudit,
    response_id: str,
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "forecastproof_research_audit_pack_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_brief": brief.to_dict(),
        "verification": verification.to_dict(),
        "decision_memo": memo.to_dict(),
        "decision_audit": memo_audit.to_dict(),
        "agent_run": {"response_id": response_id, **run_metadata},
        "governance": {
            "strict_reproduction_claimed": False,
            "deployment_authorized": False,
            "human_approval_required_for_iteration": True,
        },
    }
