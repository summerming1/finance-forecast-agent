from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from .forecastproof import (
    APP_VERSION,
    DEFAULT_VALUE_HURDLE,
    DecisionMemo,
    EvidenceBrief,
    VerificationResult,
    audit_decision_memo,
    build_audit_pack,
    build_replay_memo,
    load_demo_brief,
    stress_test_decision,
    verify_demo_claim,
)
from .openai_responses import OpenAIResponsesDecisionAgent
from .benchmark import BenchmarkTask
from .iteration_lab import (
    ControlledIterationResult,
    build_iteration_proposals,
    diagnose_prediction_artifact,
    iteration_fold_partition,
    load_lineage,
    run_controlled_iteration,
)


DEMO_STATE_KEYS = (
    "forecastproof_evidence_locked",
    "forecastproof_verification_complete",
    "forecastproof_live_memo",
    "forecastproof_live_response_id",
    "forecastproof_live_run_metadata",
    "forecastproof_memo_mode",
    "forecastproof_tolerance",
    "forecastproof_value_hurdle",
    "forecastproof_reasoning_effort",
    "forecastproof_max_output_tokens",
    "iteration_lab_result",
)

PROJECT_DIR = Path(__file__).resolve().parents[2] / "projects" / "finance_agent"


@st.cache_data(show_spinner=False)
def _demo_brief():
    return load_demo_brief()


@st.cache_data(show_spinner=False)
def _demo_verification():
    return verify_demo_claim()


def render_home() -> None:
    brief = _demo_brief()
    verification = _demo_verification()

    st.title("ForecastProof")
    st.subheader("Turn forecasting research into an auditable go/no-go decision")
    st.caption(
        "An evidence-first forecasting copilot built for OpenAI Build Week. "
        f"The verified demo works without an API key; live mode uses GPT-5.6. · {APP_VERSION}"
    )
    st.markdown(":green-badge[Verified sample] :blue-badge[GPT-5.6 live mode] :gray-badge[Research use only]")
    st.info(
        "AI summarizes; deterministic gates decide. Model output can explain evidence, but it cannot change a gate.",
        icon=":material/security:",
    )

    baseline = verification.baseline_comparison
    with st.container(horizontal=True):
        st.metric("Evidence spans", verification.evidence_span_count, border=True)
        st.metric("Reproduction gates", f"{verification.gates_passed}/4", border=True)
        st.metric("Naive value gate", "HOLD" if not baseline.value_gate else "PASS", border=True)
        st.metric("Deployment", baseline.deployment_status, border=True)

    with st.container(border=True):
        st.markdown("#### The result that matters")
        result_columns = st.columns(2)
        with result_columns[0]:
            st.badge("Reproduction passed", color="green", icon=":material/check_circle:")
            st.write(
                f"DLinear reproduced the paper within tolerance: local MSE "
                f"{verification.local_metrics['mse']:.6f}."
            )
        with result_columns[1]:
            st.badge("Incremental value on hold", color="orange", icon=":material/pause_circle:")
            st.write(
                f"Versus persistence, MSE improves only {baseline.relative_improvements['mse']:.2%} "
                f"and MAE regresses {abs(baseline.relative_improvements['mae']):.2%}."
            )
        st.caption("ForecastProof distinguishes scientific reproducibility from deployment readiness.")

    st.subheader("One claim. Five auditable layers.")
    with st.container(horizontal=True):
        with st.container(border=True):
            st.markdown(":material/article:")
            st.markdown("#### 1. Analyze")
            st.write("Extract the claim, protocol, unknowns, and source-revision evidence from a verified MethodCard.")
        with st.container(border=True):
            st.markdown(":material/fact_check:")
            st.markdown("#### 2. Verify")
            st.write("Replay deterministic evidence, protocol, dataset, and metric gates against a native-run artifact.")
        with st.container(border=True):
            st.markdown(":material/experiment:")
            st.markdown("#### 3. Challenge")
            st.write("Compare the model with persistence and expose the thresholds that would flip the decision.")
        with st.container(border=True):
            st.markdown(":material/description:")
            st.markdown("#### 4. Decide")
            st.write("Generate a cited decision memo that separates reproduced facts from deployment risks.")
        with st.container(border=True):
            st.markdown(":material/model_training:")
            st.markdown("#### 5. Iterate")
            st.write("Diagnose weak slices, approve one bounded child run, and audit whether it earns research promotion.")

    with st.container(horizontal=True):
        st.page_link(
            "app_pages/analyze.py",
            label="Start the 3-minute verified demo",
            icon=":material/play_arrow:",
        )
        if st.button("Reset demo", icon=":material/restart_alt:"):
            for key in DEMO_STATE_KEYS:
                st.session_state.pop(key, None)
            st.toast("Demo state reset", icon=":material/check_circle:")

    with st.container(border=True):
        st.markdown("#### The demo question")
        st.write(brief.claim)
        st.caption(f"{brief.title} · {brief.dataset} · {brief.horizon}")

    st.subheader("Why ForecastProof")
    st.markdown(
        """
- **Research claims become inspectable objects.** Every protocol field points back to a pinned source revision.
- **The model does not grade its own work.** Deterministic code decides whether evidence, protocol, data, and metrics pass.
- **Reproduction is challenged, not celebrated blindly.** A same-window persistence baseline tests incremental value.
- **The output is decision-shaped.** Teams get a cited memo with facts, risks, actions, and an explicit guardrail.
"""
    )

    with st.expander("Built during OpenAI Build Week", icon=":material/history_edu:"):
        before, during = st.columns(2)
        with before.container(border=True):
            st.markdown("#### Before · research harness")
            st.write("Seven-stage literature, MethodCard, reproduction, benchmark, and audit workspace.")
            st.caption("Documented pre-event baseline: ffa048e")
        with during.container(border=True):
            st.markdown("#### During · judge-ready product")
            st.write(
                "ForecastProof golden path, GPT-5.6 Responses agent, deterministic memo audit, "
                "naive-challenger gate, decision stress test, cost telemetry, complete Audit Pack, and product tests."
            )
            st.caption("Built with Codex on codex/openai-build-week")


def render_analyze() -> None:
    brief = _demo_brief()
    st.title("Analyze the claim")
    st.caption("Verified sample · replayable without an API key")
    st.info(
        "This sample is backed by a strict MethodCard assembled from the paper, official repository, "
        "and a frozen dataset manifest.",
        icon=":material/verified:",
    )

    with st.container(border=True):
        st.subheader(brief.title)
        st.link_button("Open paper", brief.paper_url, icon=":material/open_in_new:")
        st.write(brief.claim)
        details = st.columns(3)
        details[0].metric("Model", brief.model)
        details[1].metric("Forecast horizon", "96 days")
        details[2].metric("Dataset", "8 channels")

    st.subheader("Claim map")
    claim_rows = [
        {"field": "Target", "verified value": "Next 96 steps for all 8 exchange-rate channels"},
        {"field": "Input", "verified value": "Prior 336 multivariate steps"},
        {"field": "Protocol", "verified value": "Chronological split; train-only scaling; seed 2021"},
        {"field": "Paper result", "verified value": "MSE 0.081 · MAE 0.203"},
    ]
    st.dataframe(claim_rows, hide_index=True, width="stretch")

    evidence_rows = [
        {
            "section": span.section.replace("_", " "),
            "source": span.source_type.replace("_", " "),
            "revision": span.source_revision,
            "evidence_id": span.evidence_id,
        }
        for span in brief.evidence_spans
    ]
    st.subheader("Pinned evidence")
    st.dataframe(evidence_rows, hide_index=True, width="stretch")
    for index, span in enumerate(brief.evidence_spans, start=1):
        with st.expander(f"Evidence {index}: {span.section.replace('_', ' ')}", icon=":material/article:"):
            st.write(span.quote)
            st.caption(f"{span.evidence_id} · {span.source_revision}")
            if span.source_url:
                st.link_button("Open source", span.source_url, icon=":material/open_in_new:")

    with st.expander("Known unknowns", icon=":material/help:"):
        for unknown in brief.unknowns:
            st.write(f"- {unknown}")

    if st.button("Lock evidence and verify", type="primary", icon=":material/arrow_forward:"):
        st.session_state["forecastproof_evidence_locked"] = True
        st.switch_page("app_pages/verify.py")


def _render_value_challenge(verification: VerificationResult) -> None:
    baseline = verification.baseline_comparison
    st.subheader("Challenge the value")
    st.caption(
        "A paper can reproduce and still add little practical forecasting value. The same frozen test windows "
        "are therefore challenged with a last-value persistence baseline."
    )
    if baseline.value_gate:
        st.success("DLinear cleared the declared naive-challenger value gate.", icon=":material/trophy:")
    else:
        st.warning(
            "Reproduction passed, but incremental value remains on HOLD.",
            icon=":material/pause_circle:",
        )

    with st.container(horizontal=True):
        st.metric(
            "MSE improvement",
            f"{baseline.relative_improvements['mse']:.2%}",
            f"Required {baseline.minimum_relative_mse_improvement:.0%}",
            delta_color="off",
            border=True,
        )
        st.metric(
            "MAE change",
            f"{baseline.relative_improvements['mae']:.2%}",
            "Regression" if baseline.relative_improvements["mae"] < 0 else "Improvement",
            delta_color="inverse" if baseline.relative_improvements["mae"] < 0 else "normal",
            border=True,
        )
        st.metric("Identical test windows", f"{baseline.test_windows:,}", border=True)
        st.metric("Deployment status", baseline.deployment_status, border=True)

    comparison_rows = pd.DataFrame(
        [
            {
                "metric": metric.upper(),
                "DLinear": baseline.model_metrics[metric],
                "Persistence": baseline.baseline_metrics[metric],
                "relative improvement": baseline.relative_improvements[metric],
                "winner": baseline.metric_winners[metric],
            }
            for metric in ("mse", "mae")
        ]
    )
    chart_frame = comparison_rows.set_index("metric")[["DLinear", "Persistence"]]
    chart, table = st.columns([1, 1.25])
    with chart.container(border=True):
        st.markdown("#### Same-window metric challenge")
        st.bar_chart(chart_frame, width="stretch")
    with table.container(border=True):
        st.markdown("#### Challenger scorecard")
        st.dataframe(
            comparison_rows,
            hide_index=True,
            width="stretch",
            column_config={
                "DLinear": st.column_config.NumberColumn(format="%.6f"),
                "Persistence": st.column_config.NumberColumn(format="%.6f"),
                "relative improvement": st.column_config.NumberColumn(format="percent"),
            },
        )
        st.caption(baseline.evaluation_space)

    st.markdown("#### Decision stress test")
    st.caption("Change governance thresholds—not the underlying result—to see exactly where the decision flips.")
    with st.form("forecastproof_stress_test", border=True):
        controls = st.columns(2)
        tolerance = controls[0].select_slider(
            "Accepted paper-metric tolerance",
            options=[0.001, 0.003, 0.0031, 0.005, 0.01, 0.02],
            value=verification.tolerance,
            format_func=lambda value: f"{value:.4f}",
            help="Both MSE and MAE deltas must remain inside this tolerance.",
            key="forecastproof_tolerance",
        )
        value_hurdle = controls[1].select_slider(
            "Required MSE improvement over persistence",
            options=[0.0, 0.005, 0.01, 0.02, 0.05],
            value=DEFAULT_VALUE_HURDLE,
            format_func=lambda value: f"{value:.1%}",
            help="The value gate also requires no MAE regression.",
            key="forecastproof_value_hurdle",
        )
        st.form_submit_button(
            "Recalculate decision boundary",
            icon=":material/tune:",
            type="primary",
        )
    stress = stress_test_decision(
        verification,
        metric_tolerance=tolerance,
        minimum_relative_mse_improvement=value_hurdle,
    )
    boundary_columns = st.columns(4)
    boundary_rows = (
        ("Reproduction", stress.reproduction_gate, "Pass" if stress.reproduction_gate else "Fail"),
        ("Naive value", stress.value_gate, "Pass" if stress.value_gate else "Hold"),
        ("Out-of-period", stress.robustness_gate, "Pass" if stress.robustness_gate else "Not tested"),
        ("Deployment", stress.deployment_status == "READY", stress.deployment_status),
    )
    for column, (label, passed, value) in zip(boundary_columns, boundary_rows, strict=True):
        with column.container(border=True):
            badge_color = "green" if passed else ("red" if value == "Fail" else "orange")
            st.badge(value, color=badge_color)
            st.markdown(f"#### {label}")
    with st.expander("Why the decision is blocked", icon=":material/block:"):
        for blocker in stress.blockers:
            st.write(f"- {blocker}")
    st.info(
        "GPT-5.6 may summarize this boundary, but it cannot change any of these deterministic gates.",
        icon=":material/lock:",
    )


def render_verify() -> None:
    verification = _demo_verification()
    st.title("Verify the reproduction")
    st.caption(
        "Verified artifact replay · deterministic checks rerun against a frozen native training report; "
        "this page does not retrain the model."
    )

    if verification.verdict == "REPRODUCED":
        st.success("Claim reproduced within the declared tolerance.", icon=":material/check_circle:")
    else:
        st.error("Claim did not pass all deterministic gates.", icon=":material/error:")

    gate_rows = [
        ("Evidence", verification.evidence_gate, f"{verification.evidence_span_count} cited spans"),
        ("Protocol", verification.protocol_gate, "Split, scaling, model, optimizer, and seed matched"),
        ("Dataset", verification.dataset_gate, "Frozen SHA-256 matched"),
        ("Metrics", verification.metric_gate, f"Absolute delta ≤ {verification.tolerance:.3f}"),
    ]
    columns = st.columns(4)
    for column, (name, passed, detail) in zip(columns, gate_rows, strict=True):
        with column.container(border=True):
            st.badge("Passed" if passed else "Failed", color="green" if passed else "red")
            st.markdown(f"#### {name}")
            st.caption(detail)

    st.subheader("Paper vs. native run")
    metric_rows = pd.DataFrame(
        {
            "metric": ["MSE", "MAE"],
            "paper": [verification.reported_metrics["mse"], verification.reported_metrics["mae"]],
            "local": [verification.local_metrics["mse"], verification.local_metrics["mae"]],
        }
    ).set_index("metric")
    st.bar_chart(metric_rows, width="stretch")
    comparison = st.columns(4)
    comparison[0].metric("Paper MSE", f"{verification.reported_metrics['mse']:.3f}")
    comparison[1].metric(
        "Local MSE",
        f"{verification.local_metrics['mse']:.6f}",
        f"Δ {verification.absolute_deltas['mse']:.6f}",
        delta_color="off",
    )
    comparison[2].metric("Paper MAE", f"{verification.reported_metrics['mae']:.3f}")
    comparison[3].metric(
        "Local MAE",
        f"{verification.local_metrics['mae']:.6f}",
        f"Δ {verification.absolute_deltas['mae']:.6f}",
        delta_color="off",
    )

    _render_value_challenge(verification)

    st.subheader("Protocol delta")
    st.caption("Paper requirements are compared with the frozen native-run protocol before metrics are accepted.")
    st.dataframe(list(verification.protocol_comparison), hide_index=True, width="stretch")

    st.subheader("Training trace")
    history = pd.DataFrame(verification.training_history)
    st.line_chart(history, x="epoch", y=["train_mse", "validation_mse"], width="stretch")

    with st.expander("Audit identifiers", icon=":material/fingerprint:"):
        st.code(f"dataset_sha256={verification.dataset_sha256}")
        st.code(f"reproduction_plan_hash={verification.reproduction_plan_hash}")
        st.code(f"artifact={verification.artifact_path}")

    if st.button("Create decision memo", type="primary", icon=":material/arrow_forward:"):
        st.session_state["forecastproof_verification_complete"] = True
        st.switch_page("app_pages/decision_memo.py")


def render_decision_memo() -> None:
    brief = _demo_brief()
    verification = _demo_verification()
    replay_memo = build_replay_memo(brief, verification)

    st.title("Decision memo")
    st.caption("The deterministic gates decide what passed. GPT-5.6 can synthesize the cited decision narrative.")
    mode = st.segmented_control(
        "Generation mode",
        ["Verified replay", "Live GPT-5.6"],
        default="Verified replay",
        key="forecastproof_memo_mode",
    )

    memo = replay_memo
    response_id = "offline-replay"
    run_metadata: dict[str, object] = {
        "generation_mode": "verified_replay",
        "request_count": 0,
        "usage": None,
    }
    if mode == "Live GPT-5.6":
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        if not has_key:
            st.warning(
                "Set OPENAI_API_KEY to run the live Responses agent. The verified replay remains visible below.",
                icon=":material/key_off:",
            )
        with st.form("forecastproof_live_run", border=True):
            st.markdown("#### Cost-controlled live run")
            st.caption(
                "One explicit submission triggers the agent. The default uses low reasoning, a hard output cap, "
                "and no automatic paid retry."
            )
            controls = st.columns(2)
            reasoning_effort = controls[0].selectbox(
                "Reasoning effort",
                ["none", "low", "medium"],
                index=1,
                help="Use low for the demo; medium can improve difficult synthesis but may consume more tokens.",
                key="forecastproof_reasoning_effort",
            )
            max_output_tokens = controls[1].select_slider(
                "Maximum output tokens",
                options=[800, 1200, 1600, 2400],
                value=1600,
                help="Each Responses API call cannot generate beyond this hard output cap.",
                key="forecastproof_max_output_tokens",
            )
            submitted = st.form_submit_button(
                "Run EvidenceAnalyst once",
                type="primary",
                icon=":material/auto_awesome:",
                disabled=not has_key,
            )
        if submitted:
            try:
                with st.spinner("GPT-5.6 is inspecting the evidence and verification tools…"):
                    run = OpenAIResponsesDecisionAgent(
                        reasoning_effort=reasoning_effort,
                        max_output_tokens=max_output_tokens,
                        retries=1,
                    ).generate(brief=brief, verification=verification)
                st.session_state["forecastproof_live_memo"] = run.memo
                st.session_state["forecastproof_live_response_id"] = run.response_id
                st.session_state["forecastproof_live_run_metadata"] = {
                    "generation_mode": "live_gpt_5_6",
                    "request_count": run.request_count,
                    "usage": run.usage.to_dict(),
                }
                st.toast("Live decision memo generated", icon=":material/check_circle:")
            except Exception as exc:
                st.error(f"Live mode failed safely: {exc}", icon=":material/error:")
        if live_memo := st.session_state.get("forecastproof_live_memo"):
            memo = live_memo
            response_id = st.session_state.get("forecastproof_live_response_id", "unknown")
            run_metadata = st.session_state.get("forecastproof_live_run_metadata", run_metadata)

    _render_memo(
        memo,
        brief=brief,
        verification=verification,
        response_id=response_id,
        run_metadata=run_metadata,
    )


def _render_memo(
    memo: DecisionMemo,
    *,
    brief: EvidenceBrief,
    verification: VerificationResult,
    response_id: str,
    run_metadata: dict[str, object],
) -> None:
    color = {"GO": "green", "CONDITIONAL": "orange", "NO_GO": "red"}[memo.recommendation]
    stress = stress_test_decision(verification)
    st.badge(memo.recommendation, color=color, icon=":material/gavel:")
    st.subheader(memo.headline)
    with st.container(horizontal=True):
        st.metric("Research result", stress.research_status, border=True)
        st.metric("Naive value gate", "PASS" if stress.value_gate else "HOLD", border=True)
        st.metric("Deployment", stress.deployment_status, border=True)
        st.metric("Decision confidence", f"{memo.confidence:.0%}", border=True)

    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("#### Why")
        for item in memo.rationale:
            st.write(f"- {item}")
    with right.container(border=True):
        st.markdown("#### Verified facts")
        for item in memo.verified_facts:
            st.write(f"- {item}")

    risks, actions = st.columns(2)
    with risks.container(border=True):
        st.markdown("#### Risks")
        for item in memo.risks:
            st.write(f"- {item}")
    with actions.container(border=True):
        st.markdown("#### Next actions")
        for item in memo.next_actions:
            st.write(f"- {item}")

    st.warning(memo.guardrail, icon=":material/policy:")

    memo_audit = audit_decision_memo(memo, brief, verification)
    st.subheader("Deterministic decision audit")
    if memo_audit.passed:
        st.success(
            "The memo passed every deterministic grounding and safety check.",
            icon=":material/verified_user:",
        )
    else:
        st.warning(
            "The memo is visible for diagnosis, but one or more audit checks failed.",
            icon=":material/warning:",
        )
    audit_metrics = st.columns(4)
    audit_metrics[0].metric("Audit score", f"{memo_audit.score}/100")
    audit_metrics[1].metric("Checks passed", f"{memo_audit.passed_checks}/{memo_audit.total_checks}")
    audit_metrics[2].metric("Valid citations", len(memo.citations))
    audit_metrics[3].metric("Required tools", "2/2" if memo_audit.checks[1].passed else "Incomplete")
    st.dataframe(
        [
            {
                "check": check.label,
                "status": "passed" if check.passed else "failed",
                "evidence": check.detail,
            }
            for check in memo_audit.checks
        ],
        hide_index=True,
        width="stretch",
    )

    with st.expander("Agent trace and citations", icon=":material/account_tree:"):
        st.caption(f"Mode: {memo.mode} · Model: {memo.model} · Response: {response_id}")
        st.write(" → ".join(memo.tool_trace))
        st.dataframe(list(memo.citations), hide_index=True, width="stretch")
        usage = run_metadata.get("usage")
        if isinstance(usage, dict):
            st.markdown("#### Token and cost telemetry")
            usage_metrics = st.columns(4)
            usage_metrics[0].metric("API requests", int(run_metadata.get("request_count", 0)))
            usage_metrics[1].metric("Input tokens", int(usage.get("input_tokens", 0)))
            usage_metrics[2].metric("Output tokens", int(usage.get("output_tokens", 0)))
            estimated_cost = usage.get("estimated_cost_usd")
            usage_metrics[3].metric(
                "Estimated cost",
                f"${float(estimated_cost):.6f}" if estimated_cost is not None else "Unavailable",
            )
            st.caption(str(usage.get("cost_basis", "")))

    payload = json.dumps(memo.to_dict(), ensure_ascii=False, indent=2)
    audit_pack = build_audit_pack(
        brief=brief,
        verification=verification,
        memo=memo,
        memo_audit=memo_audit,
        response_id=response_id,
        run_metadata=run_metadata,
    )
    with st.container(horizontal=True):
        st.download_button(
            "Download memo JSON",
            data=payload,
            file_name="forecastproof_decision_memo.json",
            mime="application/json",
            icon=":material/download:",
        )
        st.download_button(
            "Download complete Audit Pack",
            data=json.dumps(audit_pack, ensure_ascii=False, indent=2),
            file_name="forecastproof_audit_pack.json",
            mime="application/json",
            icon=":material/inventory_2:",
            type="primary",
        )


@st.cache_data(show_spinner=False)
def _load_iteration_suite() -> dict:
    return json.loads((PROJECT_DIR / "reports" / "multi_benchmark_suite.json").read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _load_iteration_card(paper_id: str) -> dict:
    path = PROJECT_DIR / "method_cards_local_llm" / f"{paper_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _render_iteration_result(result: ControlledIterationResult | dict) -> None:
    payload = result.to_dict() if isinstance(result, ControlledIterationResult) else result
    checks = payload["checks"]
    promoted = all(check["passed"] for check in checks)
    if promoted:
        st.success(
            "The child passed every gate and may enter the research-candidate pool. Deployment is still unauthorized.",
            icon=":material/verified:",
        )
    else:
        st.warning(
            "The child did not clear every guardrail, so the parent remains the research incumbent.",
            icon=":material/shield_with_heart:",
        )
    with st.container(horizontal=True):
        st.metric("Decision", payload["decision"].replace("_", " "), border=True)
        st.metric("Primary improvement", f"{payload['primary_improvement']:.2%}", border=True)
        st.metric("Runtime", f"{payload['runtime_seconds']:.2f}s", border=True)
        st.metric("Deployment", "Unauthorized", border=True)
    metric_rows = []
    for metric, parent_value in payload["parent_metrics"].items():
        if metric in payload["child_metrics"]:
            child_value = payload["child_metrics"][metric]
            metric_rows.append(
                {
                    "metric": metric,
                    "parent": parent_value,
                    "child": child_value,
                    "delta": child_value - parent_value,
                }
            )
    st.dataframe(
        metric_rows,
        hide_index=True,
        width="stretch",
        column_config={
            "parent": st.column_config.NumberColumn(format="%.6f"),
            "child": st.column_config.NumberColumn(format="%.6f"),
            "delta": st.column_config.NumberColumn(format="%+.6f"),
        },
    )
    st.dataframe(
        [
            {"gate": check["label"], "status": "passed" if check["passed"] else "failed", "detail": check["detail"]}
            for check in checks
        ],
        hide_index=True,
        width="stretch",
    )


def render_iteration_lab() -> None:
    st.title("Evidence-guided iteration lab")
    st.caption("Diagnose → propose → approve one bounded run → promote or retain · no LLM or API cost")
    st.info(
        "Strict reproduction stays immutable. This page creates a separate controlled_iteration child, and a passing "
        "result can become only a research candidate—not a deployable model.",
        icon=":material/account_tree:",
    )
    suite = _load_iteration_suite()
    task_rows = suite["tasks"]
    task_by_id = {row["task"]["task_id"]: row for row in task_rows}
    task_ids = list(task_by_id)
    default_task = "spy_daily_next_5d_volatility_v1"
    task_id = st.selectbox(
        "Frozen benchmark task",
        task_ids,
        index=task_ids.index(default_task) if default_task in task_ids else 0,
        format_func=lambda value: value.replace("_v1", "").replace("_", " "),
        key="iteration_task_id",
    )
    task_row = task_by_id[task_id]
    reports = task_row["reports"]
    method_ids = [row["method_id"] for row in reports]
    default_method = "arxiv_2310_16855"
    method_id = st.selectbox(
        "Parent method",
        method_ids,
        index=method_ids.index(default_method) if default_method in method_ids else 0,
        format_func=lambda value: f"{value} · {next(row['model_family'] for row in reports if row['method_id'] == value)}",
        key="iteration_method_id",
    )
    parent_report = next(row for row in reports if row["method_id"] == method_id)
    task = BenchmarkTask.from_dict(task_row["task"])
    diagnostic_folds, promotion_folds = iteration_fold_partition(parent_report["prediction_artifact"])
    diagnostics = diagnose_prediction_artifact(parent_report["prediction_artifact"], fold_ids=diagnostic_folds)
    card = _load_iteration_card(method_id)

    st.subheader("1. Diagnose where the parent loses")
    with st.container(horizontal=True):
        st.metric("Development rows", f"{diagnostics.observations:,}", border=True)
        st.metric("Global MAE", f"{diagnostics.global_metrics['mae']:.6f}", border=True)
        st.metric("Fold MAE variation", f"{diagnostics.fold_mae_cv:.1%}", border=True)
        st.metric("Large/quiet MAE", f"{diagnostics.high_move_mae_ratio:.2f}×", border=True)
        st.metric("Untouched holdout", f"{len(promotion_folds)} folds", border=True)
    for finding in diagnostics.findings:
        st.write(f"- {finding}")
    slice_rows = [item.to_dict() for item in diagnostics.slices]
    regime_rows = [row for row in slice_rows if row["dimension"] == "realized_move_regime"]
    fold_rows = [row for row in slice_rows if row["dimension"] == "fold"]
    charts = st.columns(2)
    with charts[0].container(border=True):
        st.markdown("#### Error by realized-move slice")
        regime_frame = pd.DataFrame(
            {"Regime": [row["label"] for row in regime_rows], "MAE": [row["mae"] for row in regime_rows]}
        )
        st.vega_lite_chart(
            regime_frame,
            {
                "mark": {"type": "bar", "tooltip": True},
                "encoding": {
                    "x": {"field": "Regime", "type": "nominal", "sort": ["quiet", "normal", "large_move"]},
                    "y": {"field": "MAE", "type": "quantitative", "scale": {"zero": True}},
                },
            },
            width="stretch",
        )
        st.caption("Descriptive test slices only; they are not an ex-ante market-state signal.")
    with charts[1].container(border=True):
        st.markdown("#### Error by chronological fold")
        fold_frame = pd.DataFrame(
            {
                "Fold": [int(row["label"].split("_")[-1]) for row in fold_rows],
                "MAE": [row["mae"] for row in fold_rows],
            }
        )
        st.vega_lite_chart(
            fold_frame,
            {
                "mark": {"type": "line", "point": True, "tooltip": True},
                "encoding": {
                    "x": {"field": "Fold", "type": "quantitative"},
                    "y": {"field": "MAE", "type": "quantitative", "scale": {"zero": True}},
                },
            },
            width="stretch",
        )

    st.subheader("2. Review evidence-bound hypotheses")
    proposals = build_iteration_proposals(task, parent_report, card)
    proposal_by_id = {proposal.proposal_id: proposal for proposal in proposals}
    selected_id = st.selectbox(
        "Proposed experiment",
        list(proposal_by_id),
        format_func=lambda value: proposal_by_id[value].title,
        key="iteration_proposal_id",
    )
    proposal = proposal_by_id[selected_id]
    with st.container(border=True):
        st.badge("Human approval required", color="orange", icon=":material/approval:")
        st.markdown(f"#### {proposal.title}")
        st.write(proposal.hypothesis)
        st.caption(proposal.expected_outcome)
        st.code(json.dumps(proposal.model_parameters, indent=2), language="json")
    st.dataframe(
        [
            {
                "type": item.evidence_type,
                "section": item.section,
                "claim": item.claim,
                "evidence ID": item.evidence_id,
                "revision": item.source_revision,
            }
            for item in proposal.evidence
        ],
        hide_index=True,
        width="stretch",
    )
    with st.expander("Safeguards and stopping conditions", icon=":material/policy:"):
        st.markdown("**Safeguards**")
        for item in proposal.safeguards:
            st.write(f"- {item}")
        st.markdown("**Stop conditions**")
        for item in proposal.stop_conditions:
            st.write(f"- {item}")

    st.subheader("3. Approve exactly one child experiment")
    with st.form("controlled_iteration_form", border=True):
        runtime_budget = st.slider(
            "Runtime budget (seconds)",
            min_value=15,
            max_value=proposal.max_runtime_seconds,
            value=min(60, proposal.max_runtime_seconds),
            step=15,
        )
        approved = st.checkbox(
            "I approve one child run on the frozen task and understand it cannot authorize deployment."
        )
        submitted = st.form_submit_button(
            "Run one controlled iteration",
            type="primary",
            icon=":material/play_arrow:",
        )
    if submitted:
        if not approved:
            st.warning("Explicit approval is required before training can start.", icon=":material/approval:")
        else:
            try:
                with st.status("Running one bounded child experiment…", expanded=True) as status:
                    st.write("Reusing the frozen dataset, target rows, and chronological folds.")
                    result = run_controlled_iteration(
                        PROJECT_DIR,
                        task,
                        parent_report,
                        proposal,
                        approved=True,
                        runtime_budget_seconds=runtime_budget,
                    )
                    st.session_state["iteration_lab_result"] = result
                    status.update(label="Controlled iteration audited", state="complete", expanded=False)
                st.toast("Child experiment and lineage saved", icon=":material/check_circle:")
            except Exception as exc:
                st.error(f"Controlled iteration stopped safely: {exc}", icon=":material/error:")
    lineage = load_lineage(PROJECT_DIR)
    result = st.session_state.get("iteration_lab_result")
    saved_payload = None
    if not result:
        latest = next((item for item in reversed(lineage) if item.get("task_id") == task_id), None)
        if latest:
            artifact_path = Path(latest["artifact_path"])
            if not artifact_path.is_absolute():
                artifact_path = PROJECT_DIR.parents[1] / artifact_path
            if artifact_path.exists():
                saved_payload = json.loads(artifact_path.read_text(encoding="utf-8"))["result"]
    if result and result.task_id == task_id:
        st.subheader("4. Deterministic promotion decision")
        _render_iteration_result(result)
    elif saved_payload:
        st.subheader("4. Latest saved promotion decision")
        st.caption("Replay of the committed child artifact; no training occurs when this page loads.")
        _render_iteration_result(saved_payload)

    if lineage:
        st.subheader("Experiment lineage")
        st.dataframe(
            list(reversed(lineage)),
            hide_index=True,
            width="stretch",
            column_config={"artifact_path": None, "model_parameters": st.column_config.JsonColumn("Parameters")},
        )
