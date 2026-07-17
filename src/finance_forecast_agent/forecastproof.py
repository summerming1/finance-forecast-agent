from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_METHOD_CARD = PROJECT_ROOT / "projects" / "finance_agent" / "method_cards_local_llm" / "arxiv_2205_13504.json"
DEFAULT_REPORT = PROJECT_ROOT / "projects" / "finance_agent" / "reports" / "native_dlinear_exchange_336_96.json"
APP_VERSION = "0.3.0-build-week"
AUDIT_PACK_SCHEMA_VERSION = "forecastproof_audit_pack_v1"


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
    artifact_path: str

    @property
    def gates_passed(self) -> int:
        return sum((self.evidence_gate, self.protocol_gate, self.dataset_gate, self.metric_gate))

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
        dataset_sha256=str(report.get("dataset", {}).get("sha256", "")),
        reproduction_plan_hash=str(governance.get("reproduction_plan_hash", "")),
        evidence_span_count=int(evidence_verification.get("span_count", 0)),
        training_history=tuple(report.get("training_history", [])),
        protocol_comparison=protocol_comparison,
        artifact_path=artifact_display,
    )


def build_replay_memo(brief: EvidenceBrief, verification: VerificationResult) -> DecisionMemo:
    recommendation = "CONDITIONAL" if verification.verdict == "REPRODUCED" else "NO_GO"
    paper_mse = verification.reported_metrics["mse"]
    local_mse = verification.local_metrics["mse"]
    return DecisionMemo(
        recommendation=recommendation,
        headline="Adopt DLinear as a reproducible research baseline, not as a trading signal.",
        confidence=0.91 if verification.verdict == "REPRODUCED" else 0.35,
        rationale=(
            f"All {verification.gates_passed}/4 deterministic gates passed against a frozen native-run artifact.",
            f"Local MSE {local_mse:.6f} is within {verification.tolerance:.3f} of the paper value {paper_mse:.3f}.",
            "The MethodCard links the claim to pinned paper, repository, and dataset evidence.",
        ),
        verified_facts=(
            f"Paper claim: MSE {paper_mse:.3f}, MAE {verification.reported_metrics['mae']:.3f}.",
            f"Native run: MSE {local_mse:.6f}, MAE {verification.local_metrics['mae']:.6f}.",
            f"Dataset SHA-256 matched: {verification.dataset_sha256}.",
            f"Evidence audit passed across {verification.evidence_span_count} spans.",
        ),
        risks=(
            "One benchmark does not establish generalization to current market regimes.",
            "The published metric is forecasting error, not economic utility or risk-adjusted return.",
            "Paper-level unknowns remain, including exact device details and whether early stopping triggered.",
        ),
        next_actions=(
            "Run the same protocol on an out-of-period financial dataset.",
            "Add naive and production incumbent baselines under identical data windows.",
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
