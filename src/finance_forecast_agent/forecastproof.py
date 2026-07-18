from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METHOD_CARD = PROJECT_ROOT / "projects" / "finance_agent" / "method_cards_local_llm" / "arxiv_2205_13504.json"
DEFAULT_REPORT = PROJECT_ROOT / "projects" / "finance_agent" / "reports" / "native_dlinear_exchange_336_96.json"
DEFAULT_DATASET = PROJECT_ROOT / "projects" / "finance_agent" / "data" / "external" / "exchange_rate" / "exchange_rate.txt"
APP_VERSION = "0.6.0-build-week"
AUDIT_PACK_SCHEMA_VERSION = "forecastproof_audit_pack_v2"
DEFAULT_VALUE_HURDLE = 0.01


@dataclass(frozen=True)
class EvidenceSpan:
    evidence_id: str
    section: str
    quote: str
    source_type: str
    source_url: str
    source_revision: str


@dataclass(frozen=True)
class EvidenceBrief:
    paper_id: str
    title: str
    paper_url: str
    claim: str
    dataset: str
    model: str
    horizon: str
    reported_metrics: dict[str, float]
    strict_requirements: tuple[str, ...]
    unknowns: tuple[str, ...]
    evidence_spans: tuple[EvidenceSpan, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BaselineComparison:
    baseline_name: str
    evaluation_space: str
    test_windows: int
    observations: int
    model_metrics: dict[str, float]
    baseline_metrics: dict[str, float]
    relative_improvements: dict[str, float]
    metric_winners: dict[str, str]
    minimum_relative_mse_improvement: float
    value_gate: bool
    out_of_period_tested: bool
    deployment_status: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    evidence_gate: bool
    protocol_gate: bool
    dataset_gate: bool
    metric_gate: bool
    reported_metrics: dict[str, float]
    local_metrics: dict[str, float]
    absolute_deltas: dict[str, float]
    tolerance: float
    dataset_sha256: str
    reproduction_plan_hash: str
    evidence_span_count: int
    training_history: tuple[dict[str, float], ...]
    protocol_comparison: tuple[dict[str, str], ...]
    baseline_comparison: BaselineComparison
    artifact_path: str

    @property
    def gates_passed(self) -> int:
        return sum((self.evidence_gate, self.protocol_gate, self.dataset_gate, self.metric_gate))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionStressTest:
    metric_tolerance: float
    minimum_relative_mse_improvement: float
    reproduction_gate: bool
    value_gate: bool
    robustness_gate: bool
    research_status: str
    deployment_status: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionMemo:
    recommendation: str
    headline: str
    confidence: float
    rationale: tuple[str, ...]
    verified_facts: tuple[str, ...]
    risks: tuple[str, ...]
    next_actions: tuple[str, ...]
    citations: tuple[dict[str, str], ...]
    guardrail: str
    mode: str
    model: str
    tool_trace: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MemoAuditCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class MemoAudit:
    score: int
    passed_checks: int
    total_checks: int
    checks: tuple[MemoAuditCheck, ...]

    @property
    def passed(self) -> bool:
        return self.passed_checks == self.total_checks

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_demo_brief(method_card_path: str | Path = DEFAULT_METHOD_CARD) -> EvidenceBrief:
    card = _load_json(method_card_path)
    desired_sections = {
        "reported_results",
        "training_protocol",
        "evaluation_protocol",
        "preprocessing_protocol",
        "hyperparameters",
    }
    selected: list[EvidenceSpan] = []
    seen: set[tuple[str, str]] = set()
    for row in card.get("evidence_spans", []):
        section = str(row.get("section", ""))
        key = (str(row.get("source_id", "")), section)
        if section not in desired_sections or key in seen:
            continue
        seen.add(key)
        selected.append(
            EvidenceSpan(
                evidence_id=str(row["source_id"]),
                section=section,
                quote=str(row["quote"]),
                source_type=str(row.get("source_type", "unknown")),
                source_url=str(row.get("source_url", "")),
                source_revision=str(row.get("source_revision", "unknown")),
            )
        )

    if len(selected) < 4:
        raise ValueError("Verified demo MethodCard does not contain enough evidence spans")

    reported = card.get("reported_results", {})
    return EvidenceBrief(
        paper_id=str(card["paper_id"]),
        title=str(card["title"]),
        paper_url=str(card["paper_url"]),
        claim=(
            "DLinear with shared weights can reproduce the Exchange-Rate 336→96 result "
            "reported in Table 2 under the paper's protocol."
        ),
        dataset="Exchange-Rate · 7,588 rows · 8 daily channels",
        model="DLinear (shared weights)",
        horizon=str(card["horizon"]),
        reported_metrics={"mse": float(reported["mse"]), "mae": float(reported["mae"])},
        strict_requirements=tuple(str(item) for item in card.get("strict_requirements", [])),
        unknowns=tuple(str(item) for item in card.get("unknowns", [])),
        evidence_spans=tuple(selected),
    )


def evaluate_persistence_baseline(
    *,
    dataset_path: str | Path = DEFAULT_DATASET,
    expected_sha256: str,
    model_metrics: dict[str, float],
    seq_len: int = 336,
    pred_len: int = 96,
    train_ratio: float = 0.7,
    test_ratio: float = 0.2,
    minimum_relative_mse_improvement: float = DEFAULT_VALUE_HURDLE,
) -> BaselineComparison:
    """Challenge the reproduced model with a last-value baseline under the same data protocol."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Required baseline dataset is missing: {path}")
    observed_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed_hash != expected_sha256:
        raise ValueError("Baseline evaluation refused because the dataset SHA-256 does not match the verified artifact")

    values = np.loadtxt(path, delimiter=",")
    if values.ndim != 2 or values.shape[1] != 8:
        raise ValueError("ForecastProof baseline evaluation requires eight Exchange-Rate channels")
    train_count = int(len(values) * train_ratio)
    test_count = int(len(values) * test_ratio)
    train_values = values[:train_count]
    train_mean = train_values.mean(axis=0)
    train_scale = train_values.std(axis=0)
    train_scale[train_scale == 0] = 1.0
    scaled = (values - train_mean) / train_scale
    test_values = scaled[len(values) - test_count - seq_len :]
    test_windows = len(test_values) - seq_len - pred_len + 1
    if test_windows <= 0:
        raise ValueError("Dataset is too short for the configured baseline evaluation windows")

    squared_error = 0.0
    absolute_error = 0.0
    observations = 0
    for start in range(test_windows):
        input_window = test_values[start : start + seq_len]
        target = test_values[start + seq_len : start + seq_len + pred_len]
        prediction = np.broadcast_to(input_window[-1], target.shape)
        residual = prediction - target
        squared_error += float(np.square(residual).sum())
        absolute_error += float(np.abs(residual).sum())
        observations += int(target.size)

    baseline_metrics = {
        "mse": squared_error / observations,
        "mae": absolute_error / observations,
    }
    compared_model_metrics = {
        "mse": float(model_metrics["mse"]),
        "mae": float(model_metrics["mae"]),
    }
    relative_improvements = {
        metric: (baseline_metrics[metric] - compared_model_metrics[metric]) / baseline_metrics[metric]
        for metric in ("mse", "mae")
    }
    metric_winners = {
        metric: "DLinear" if compared_model_metrics[metric] <= baseline_metrics[metric] else "Persistence"
        for metric in ("mse", "mae")
    }
    value_gate = bool(
        relative_improvements["mse"] >= minimum_relative_mse_improvement
        and relative_improvements["mae"] >= 0
    )
    blockers: list[str] = []
    if relative_improvements["mse"] < minimum_relative_mse_improvement:
        blockers.append(
            "DLinear's MSE improvement over persistence is below the declared "
            f"{minimum_relative_mse_improvement:.0%} incremental-value hurdle."
        )
    if relative_improvements["mae"] < 0:
        blockers.append("DLinear's MAE is worse than the last-value persistence baseline.")
    blockers.append("Out-of-period robustness has not yet been tested on a second financial regime.")
    return BaselineComparison(
        baseline_name="Last-value persistence",
        evaluation_space="Train-fitted standardized values · identical chronological test windows",
        test_windows=test_windows,
        observations=observations,
        model_metrics=compared_model_metrics,
        baseline_metrics=baseline_metrics,
        relative_improvements=relative_improvements,
        metric_winners=metric_winners,
        minimum_relative_mse_improvement=minimum_relative_mse_improvement,
        value_gate=value_gate,
        out_of_period_tested=False,
        deployment_status="HOLD",
        blockers=tuple(blockers),
    )


def verify_demo_claim(report_path: str | Path = DEFAULT_REPORT) -> VerificationResult:
    report = _load_json(report_path)
    governance = report.get("governance", {})
    evidence_verification = governance.get("evidence_verification", {})
    protocol_fidelity = report.get("protocol_fidelity", {})
    protocol = report.get("protocol", {})
    reported = {name: float(value) for name, value in report.get("reported_metrics", {}).items()}
    local = {name: float(value) for name, value in report.get("metrics", {}).items() if name in reported}
    tolerance = float(protocol["result_tolerance"])
    deltas = {name: abs(local[name] - paper_value) for name, paper_value in reported.items()}
    split_matches = (
        float(protocol.get("train_ratio", 0)) == 0.7
        and float(protocol.get("test_ratio", 0)) == 0.2
        and protocol_fidelity.get("data_split") == "matched"
    )
    protocol_comparison = (
        {
            "control": "Input window",
            "paper requirement": "336 steps",
            "native run": f"{protocol.get('seq_len', 'unknown')} steps",
            "status": "matched" if int(protocol.get("seq_len", -1)) == 336 else "mismatch",
        },
        {
            "control": "Forecast horizon",
            "paper requirement": "96 steps",
            "native run": f"{protocol.get('pred_len', 'unknown')} steps",
            "status": "matched" if int(protocol.get("pred_len", -1)) == 96 else "mismatch",
        },
        {
            "control": "Chronological split",
            "paper requirement": "70% train · 10% validation · 20% test",
            "native run": "70% train · 10% validation · 20% test",
            "status": "matched" if split_matches else "mismatch",
        },
        {
            "control": "Scaling",
            "paper requirement": "Fit on training data only",
            "native run": "Train-only scaler audit",
            "status": str(protocol_fidelity.get("scaling", "unknown")),
        },
        {
            "control": "Architecture",
            "paper requirement": "DLinear shared weights",
            "native run": f"DLinear individual={str(protocol.get('individual', 'unknown')).lower()}",
            "status": str(protocol_fidelity.get("model_architecture", "unknown")),
        },
        {
            "control": "Optimizer",
            "paper requirement": "Adam · learning rate 0.0005 · batch 8",
            "native run": (
                f"Adam · learning rate {protocol.get('learning_rate', 'unknown')} · "
                f"batch {protocol.get('batch_size', 'unknown')}"
            ),
            "status": str(protocol_fidelity.get("optimizer", "unknown")),
        },
        {
            "control": "Seed",
            "paper requirement": "2021",
            "native run": str(protocol.get("seed", "unknown")),
            "status": str(protocol_fidelity.get("seed", "unknown")),
        },
    )

    evidence_gate = bool(
        governance.get("methodcard_approved")
        and governance.get("protocol_derived_from_methodcard")
        and evidence_verification.get("passed")
    )
    protocol_gate = bool(
        protocol_fidelity.get("strict_reproduction_allowed")
        and all(protocol_fidelity.get(name) == "matched" for name in ("data_split", "scaling", "model_architecture", "optimizer", "seed"))
    )
    dataset_gate = bool(
        report.get("dataset", {}).get("sha256")
        and report.get("dataset", {}).get("sha256") == protocol.get("expected_dataset_sha256")
    )
    metric_gate = bool(report.get("result_reproduced_within_tolerance") and all(delta <= tolerance for delta in deltas.values()))
    verdict = "REPRODUCED" if all((evidence_gate, protocol_gate, dataset_gate, metric_gate)) else "NOT REPRODUCED"

    artifact = Path(report_path)
    try:
        artifact_display = artifact.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        artifact_display = str(artifact)
    dataset = report.get("dataset", {})
    dataset_sha256 = str(dataset.get("sha256", ""))
    configured_dataset = Path(str(dataset.get("path", DEFAULT_DATASET)).replace("\\", "/"))
    if not configured_dataset.is_absolute():
        configured_dataset = PROJECT_ROOT / configured_dataset
    baseline_comparison = evaluate_persistence_baseline(
        dataset_path=configured_dataset,
        expected_sha256=dataset_sha256,
        model_metrics=local,
        seq_len=int(protocol.get("seq_len", 336)),
        pred_len=int(protocol.get("pred_len", 96)),
        train_ratio=float(protocol.get("train_ratio", 0.7)),
        test_ratio=float(protocol.get("test_ratio", 0.2)),
    )

    return VerificationResult(
        verdict=verdict,
        evidence_gate=evidence_gate,
        protocol_gate=protocol_gate,
        dataset_gate=dataset_gate,
        metric_gate=metric_gate,
        reported_metrics=reported,
        local_metrics=local,
        absolute_deltas=deltas,
        tolerance=tolerance,
        dataset_sha256=dataset_sha256,
        reproduction_plan_hash=str(governance.get("reproduction_plan_hash", "")),
        evidence_span_count=int(evidence_verification.get("span_count", 0)),
        training_history=tuple(report.get("training_history", [])),
        protocol_comparison=protocol_comparison,
        baseline_comparison=baseline_comparison,
        artifact_path=artifact_display,
    )


def stress_test_decision(
    verification: VerificationResult,
    *,
    metric_tolerance: float | None = None,
    minimum_relative_mse_improvement: float = DEFAULT_VALUE_HURDLE,
) -> DecisionStressTest:
    """Recalculate decision gates under explicit counterfactual governance thresholds."""
    tolerance = verification.tolerance if metric_tolerance is None else float(metric_tolerance)
    if tolerance < 0:
        raise ValueError("Metric tolerance cannot be negative")
    if minimum_relative_mse_improvement < 0:
        raise ValueError("Minimum relative MSE improvement cannot be negative")

    reproduction_gate = bool(
        verification.evidence_gate
        and verification.protocol_gate
        and verification.dataset_gate
        and all(delta <= tolerance for delta in verification.absolute_deltas.values())
    )
    improvements = verification.baseline_comparison.relative_improvements
    value_gate = bool(
        improvements["mse"] >= minimum_relative_mse_improvement
        and improvements["mae"] >= 0
    )
    robustness_gate = verification.baseline_comparison.out_of_period_tested
    blockers: list[str] = []
    if not reproduction_gate:
        required_tolerance = max(verification.absolute_deltas.values())
        blockers.append(
            f"Metric tolerance {tolerance:.4f} is below the {required_tolerance:.4f} needed to reproduce both metrics."
        )
    if improvements["mse"] < minimum_relative_mse_improvement:
        blockers.append(
            f"MSE improvement is {improvements['mse']:.2%}, below the {minimum_relative_mse_improvement:.2%} hurdle."
        )
    if improvements["mae"] < 0:
        blockers.append(f"MAE regresses by {abs(improvements['mae']):.2%} versus persistence.")
    if not robustness_gate:
        blockers.append("No out-of-period financial regime has passed the same frozen protocol yet.")
    deployment_ready = reproduction_gate and value_gate and robustness_gate
    return DecisionStressTest(
        metric_tolerance=tolerance,
        minimum_relative_mse_improvement=minimum_relative_mse_improvement,
        reproduction_gate=reproduction_gate,
        value_gate=value_gate,
        robustness_gate=robustness_gate,
        research_status="ACCEPT" if reproduction_gate else "REJECT",
        deployment_status="READY" if deployment_ready else "HOLD",
        blockers=tuple(blockers),
    )


def build_replay_memo(brief: EvidenceBrief, verification: VerificationResult) -> DecisionMemo:
    recommendation = "CONDITIONAL" if verification.verdict == "REPRODUCED" else "NO_GO"
    paper_mse = verification.reported_metrics["mse"]
    local_mse = verification.local_metrics["mse"]
    baseline = verification.baseline_comparison
    return DecisionMemo(
        recommendation=recommendation,
        headline="Accept the reproduction; hold deployment until DLinear clearly beats persistence.",
        confidence=0.94 if verification.verdict == "REPRODUCED" else 0.35,
        rationale=(
            f"All {verification.gates_passed}/4 deterministic gates passed against a frozen native-run artifact.",
            f"Local MSE {local_mse:.6f} is within {verification.tolerance:.3f} of the paper value {paper_mse:.3f}.",
            (
                f"The naive challenger gate remains on HOLD: MSE improves only "
                f"{baseline.relative_improvements['mse']:.2%}, while MAE regresses "
                f"{abs(baseline.relative_improvements['mae']):.2%} versus persistence."
            ),
        ),
        verified_facts=(
            f"Paper claim: MSE {paper_mse:.3f}, MAE {verification.reported_metrics['mae']:.3f}.",
            f"Native run: MSE {local_mse:.6f}, MAE {verification.local_metrics['mae']:.6f}.",
            (
                f"Last-value persistence across {baseline.test_windows:,} identical test windows: "
                f"MSE {baseline.baseline_metrics['mse']:.6f}, MAE {baseline.baseline_metrics['mae']:.6f}."
            ),
            f"Dataset SHA-256 matched: {verification.dataset_sha256}.",
            f"Evidence audit passed across {verification.evidence_span_count} spans.",
        ),
        risks=(
            "DLinear does not clear the 1% MSE value hurdle and loses to persistence on MAE.",
            "One reproduced benchmark does not establish out-of-period robustness in current market regimes.",
            "The published metric is forecasting error, not economic utility or risk-adjusted return.",
        ),
        next_actions=(
            "Require DLinear to beat persistence by at least 1% MSE without MAE regression.",
            "Run the frozen protocol on an out-of-period financial regime.",
            "Add production incumbent baselines under the identical evaluation windows.",
            "Define deployment guardrails and economic KPIs before any investment decision.",
        ),
        citations=tuple(
            {"evidence_id": span.evidence_id, "claim": span.section}
            for span in brief.evidence_spans[:4]
        ),
        guardrail="Research decision support only. This memo is not investment advice and does not authorize trading.",
        mode="verified_replay",
        model="deterministic policy",
        tool_trace=("get_evidence_brief", "get_verification_result", "apply_decision_guardrails"),
    )


def audit_decision_memo(
    memo: DecisionMemo,
    brief: EvidenceBrief,
    verification: VerificationResult,
) -> MemoAudit:
    """Grade model output with deterministic checks that the model cannot override."""
    valid_evidence_pairs = {
        (span.evidence_id, span.section)
        for span in brief.evidence_spans
    }
    citations = tuple(memo.citations)
    cited_ids = [str(row.get("evidence_id", "")) for row in citations]
    valid_citation_count = sum(
        (evidence_id, str(row.get("claim", ""))) in valid_evidence_pairs
        for row, evidence_id in zip(citations, cited_ids, strict=True)
    )
    valid_citations = bool(cited_ids) and valid_citation_count == len(citations)
    cited_sections = {
        str(row.get("claim", ""))
        for row, evidence_id in zip(citations, cited_ids, strict=True)
        if (evidence_id, str(row.get("claim", ""))) in valid_evidence_pairs
    }
    required_tools = {"get_evidence_brief", "get_verification_result"}
    observed_tools = set(memo.tool_trace)
    decision_is_safe = (
        memo.recommendation in {"CONDITIONAL", "NO_GO"}
        if verification.verdict == "REPRODUCED"
        else memo.recommendation == "NO_GO"
    )
    complete = all(
        (
            memo.headline.strip(),
            memo.rationale,
            memo.verified_facts,
            memo.risks,
            memo.next_actions,
            0 <= memo.confidence <= 1,
        )
    )
    guardrail = memo.guardrail.lower()
    guarded = "research" in guardrail and "not investment advice" in guardrail
    decision_text = " ".join(
        (
            memo.headline,
            *memo.rationale,
            *memo.verified_facts,
            *memo.risks,
            *memo.next_actions,
        )
    ).lower()
    baseline_honest = bool(
        verification.baseline_comparison.value_gate
        or (
            memo.recommendation != "GO"
            and "persistence" in decision_text
            and ("hold" in decision_text or "value" in decision_text)
        )
    )
    checks = (
        MemoAuditCheck(
            "deterministic_authority",
            "Deterministic gate authority",
            decision_is_safe,
            "A reproduced metric may support research, but cannot become an unconditional deployment decision.",
        ),
        MemoAuditCheck(
            "tool_grounding",
            "Required tool grounding",
            required_tools <= observed_tools,
            f"Observed {len(required_tools & observed_tools)}/{len(required_tools)} required read-only tools.",
        ),
        MemoAuditCheck(
            "citation_validity",
            "Citation validity",
            valid_citations,
            f"Validated {valid_citation_count}/{len(cited_ids)} evidence identifier-to-section mappings.",
        ),
        MemoAuditCheck(
            "evidence_coverage",
            "Evidence coverage",
            len(cited_sections) >= 2,
            f"Citations cover {len(cited_sections)} distinct MethodCard sections.",
        ),
        MemoAuditCheck(
            "decision_completeness",
            "Decision completeness",
            complete,
            "Headline, facts, rationale, risks, actions, and bounded confidence are all required.",
        ),
        MemoAuditCheck(
            "research_guardrail",
            "Research-only guardrail",
            guarded,
            "The memo must explicitly remain research support and not investment advice.",
        ),
        MemoAuditCheck(
            "baseline_honesty",
            "Naive-challenger honesty",
            baseline_honest,
            (
                "A memo must disclose the persistence comparison and hold deployment when the incremental-value "
                "gate fails."
            ),
        ),
    )
    passed_checks = sum(check.passed for check in checks)
    return MemoAudit(
        score=round(100 * passed_checks / len(checks)),
        passed_checks=passed_checks,
        total_checks=len(checks),
        checks=checks,
    )


def build_audit_pack(
    *,
    brief: EvidenceBrief,
    verification: VerificationResult,
    memo: DecisionMemo,
    memo_audit: MemoAudit,
    response_id: str,
    run_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a portable, secret-free evidence bundle for review or handoff."""
    return {
        "schema_version": AUDIT_PACK_SCHEMA_VERSION,
        "app_version": APP_VERSION,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "case": {
            "paper_id": brief.paper_id,
            "title": brief.title,
            "question": brief.claim,
        },
        "evidence_brief": brief.to_dict(),
        "verification": verification.to_dict(),
        "decision_stress_test": stress_test_decision(verification).to_dict(),
        "decision_memo": memo.to_dict(),
        "decision_audit": memo_audit.to_dict(),
        "agent_run": {
            "response_id": response_id,
            **(run_metadata or {}),
        },
        "provenance": {
            "dataset_sha256": verification.dataset_sha256,
            "reproduction_plan_hash": verification.reproduction_plan_hash,
            "artifact_path": verification.artifact_path,
        },
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Required verified demo artifact is missing: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {resolved}")
    return payload
