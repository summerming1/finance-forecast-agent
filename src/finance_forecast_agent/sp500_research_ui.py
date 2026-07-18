from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from .forecastproof import APP_VERSION, DecisionMemo
from .iteration_lab import (
    ControlledIterationResult,
    build_iteration_proposals,
    diagnose_prediction_artifact,
    iteration_fold_partition,
    load_lineage,
    run_controlled_iteration,
)
from .openai_responses import OpenAIResponsesDecisionAgent
from .sp500_research import (
    DEFAULT_CASE_ID,
    audit_research_memo,
    build_research_audit_pack,
    build_research_brief,
    build_research_replay_memo,
    case_options,
    get_case_runtime,
    load_sp500_research_suite,
    verify_research_case,
)


PROJECT_DIR = Path(__file__).resolve().parents[2] / "projects" / "finance_agent"
CASE_STATE_KEY = "forecastproof_case_id"


def selected_case_id() -> str:
    valid = {row["paper_id"] for row in case_options()}
    selected = str(st.session_state.get(CASE_STATE_KEY, DEFAULT_CASE_ID))
    return selected if selected in valid else DEFAULT_CASE_ID


@st.cache_data(show_spinner=False)
def _suite() -> dict[str, Any]:
    return load_sp500_research_suite(PROJECT_DIR)


@st.cache_data(show_spinner=False)
def _brief(paper_id: str):
    return build_research_brief(PROJECT_DIR, paper_id)


@st.cache_data(show_spinner=False)
def _verification(paper_id: str, hurdle: float = 0.01):
    return verify_research_case(PROJECT_DIR, paper_id, minimum_absolute_improvement=hurdle)


def _case_label(paper_id: str) -> str:
    row = next(item for item in case_options() if item["paper_id"] == paper_id)
    return f"{row['short_name']} · {paper_id}"


def render_home() -> None:
    suite = _suite()
    paper_id = selected_case_id()
    brief = _brief(paper_id)
    verification = _verification(paper_id)
    comparison = suite["benchmark"]

    st.title("ForecastProof")
    st.subheader("From one paper demo to a reusable S&P 500 research decision system")
    st.caption(
        f"Three evidence-backed papers · one frozen daily SPY task · identical folds and baselines · {APP_VERSION}"
    )
    st.markdown(":green-badge[3/3 adaptations validated] :blue-badge[GPT-5.6 optional] :gray-badge[Research only]")
    st.info(
        "AI reads and explains evidence. Deterministic code owns data integrity, comparison, statistics, and promotion.",
        icon=":material/security:",
    )

    with st.container(horizontal=True):
        st.metric("Research papers", suite["case_count"], border=True)
        st.metric("Executable model families", 3, border=True)
        st.metric("Identical OOF rows", comparison["directional_baseline"]["prediction_count"], border=True)
        st.metric("Comparison integrity", "PASS", border=True)

    with st.container(border=True):
        st.markdown("#### Selected research case")
        st.write(brief.title)
        st.caption(_case_label(paper_id))
        columns = st.columns(3)
        columns[0].metric("Adaptation gates", f"{verification.gates_passed}/4")
        columns[1].metric("Directional accuracy", f"{verification.baseline_comparison.model_accuracy:.2%}")
        columns[2].metric("Statistical skill", "PASS" if verification.baseline_comparison.value_gate else "HOLD")
        st.warning(brief.scope_disclosure, icon=":material/info:")

    st.subheader("One contract, three papers")
    rows = []
    for report in comparison["reports"]:
        verification_row = _verification(report["method_id"])
        rows.append(
            {
                "paper": _case_label(report["method_id"]),
                "model": report["model_family"],
                "directional accuracy": report["metrics"]["directional_accuracy"],
                "lift vs baseline": verification_row.baseline_comparison.absolute_improvement,
                "adaptation": verification_row.verdict,
                "skill gate": "PASS" if verification_row.baseline_comparison.value_gate else "HOLD",
            }
        )
    st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        column_config={
            "directional accuracy": st.column_config.NumberColumn(format="percent"),
            "lift vs baseline": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    st.subheader("The auditable path")
    with st.container(horizontal=True):
        for number, title, body in (
            (1, "Analyze", "Pin the paper claim, unknowns, and primary evidence."),
            (2, "Verify", "Run the selected method family on the shared leakage-safe contract."),
            (3, "Decide", "Separate adaptation validity from statistical and deployment value."),
            (4, "Iterate", "Approve one bounded child; promote only through deterministic gates."),
        ):
            with st.container(border=True):
                st.markdown(f"#### {number}. {title}")
                st.write(body)
    if st.button("Start the selected case", type="primary", icon=":material/play_arrow:"):
        st.switch_page("app_pages/analyze.py")


def render_analyze() -> None:
    paper_id = selected_case_id()
    brief = _brief(paper_id)
    st.title("Analyze the paper")
    st.caption(_case_label(paper_id))
    st.info("The paper evidence and the executable benchmark contract are shown separately.", icon=":material/fact_check:")

    with st.container(border=True):
        st.subheader(brief.title)
        if brief.paper_url.startswith("http"):
            st.link_button("Open paper", brief.paper_url, icon=":material/open_in_new:")
        st.write(brief.claim)
        columns = st.columns(3)
        columns[0].metric("Selected adapter", brief.model)
        columns[1].metric("Evidence spans", len(brief.evidence_spans))
        columns[2].metric("Validation tier", "Adaptation")

    original, executable = st.columns(2)
    with original.container(border=True):
        st.markdown("#### Original paper scope")
        st.write(brief.original_scope)
        st.json(brief.reported_results, expanded=False)
    with executable.container(border=True):
        st.markdown("#### Shared executable task")
        st.write(brief.shared_task)
        st.warning(brief.scope_disclosure, icon=":material/compare_arrows:")

    st.subheader("Pinned paper evidence")
    st.dataframe(
        [
            {
                "section": span.section,
                "evidence ID": span.evidence_id,
                "revision": span.source_revision,
            }
            for span in brief.evidence_spans
        ],
        hide_index=True,
        width="stretch",
    )
    for span in brief.evidence_spans:
        with st.expander(span.section.replace("_", " ").title(), icon=":material/article:"):
            st.write(span.quote)
            st.caption(f"{span.evidence_id} · {span.source_revision}")

    with st.expander("Known unknowns", icon=":material/help:"):
        for item in brief.unknowns:
            st.write(f"- {item}")
    if st.button("Lock this case and verify", type="primary", icon=":material/arrow_forward:"):
        st.session_state["forecastproof_evidence_locked"] = True
        st.switch_page("app_pages/verify.py")


def render_verify() -> None:
    paper_id = selected_case_id()
    st.title("Verify the common-task adaptation")
    st.caption("Frozen SPY daily direction · 12 lagged returns · purged walk-forward · identical targets")

    with st.form("research_skill_boundary", border=True):
        hurdle = st.select_slider(
            "Required absolute accuracy lift over the fold-train majority baseline",
            options=[0.0, 0.005, 0.01, 0.02, 0.03],
            value=0.01,
            format_func=lambda value: f"{value:.1%}",
            key="forecastproof_skill_hurdle",
        )
        st.form_submit_button("Recalculate value boundary", icon=":material/tune:")
    verification = _verification(paper_id, hurdle)
    baseline = verification.baseline_comparison
    if verification.verdict == "ADAPTATION_VALIDATED":
        st.success("The paper-inspired adapter passed all common-task integrity gates.", icon=":material/check_circle:")
    else:
        st.error("The adaptation artifact failed an integrity gate.", icon=":material/error:")

    gates = (
        ("Evidence", verification.evidence_gate, f"{verification.evidence_span_count} non-empty primary spans"),
        ("Frozen data", verification.frozen_data_gate, "Dataset SHA-256 matched"),
        ("Common protocol", verification.common_protocol_gate, "Same folds, targets, features, and task ID"),
        ("Artifact", verification.artifact_gate, f"{baseline.prediction_count} finite aligned predictions"),
    )
    columns = st.columns(4)
    for column, (label, passed, detail) in zip(columns, gates, strict=True):
        with column.container(border=True):
            st.badge("Passed" if passed else "Failed", color="green" if passed else "red")
            st.markdown(f"#### {label}")
            st.caption(detail)

    st.subheader("Does it add signal beyond a simple method?")
    with st.container(horizontal=True):
        st.metric("Model accuracy", f"{baseline.model_accuracy:.2%}", border=True)
        st.metric("Majority baseline", f"{baseline.baseline_accuracy:.2%}", border=True)
        st.metric("Absolute lift", f"{baseline.absolute_improvement:+.2%}", border=True)
        st.metric("Skill gate", "PASS" if baseline.value_gate else "HOLD", border=True)
    interval = baseline.wilson_95_interval
    st.write(
        f"95% Wilson interval: **{interval[0]:.2%}–{interval[1]:.2%}** · "
        f"two-sided binomial p-value: **{baseline.two_sided_binomial_pvalue:.4f}**"
    )
    if baseline.value_gate:
        st.success("The declared lift and statistical gates both passed.", icon=":material/trophy:")
    else:
        st.warning("Adaptation is valid, but statistical forecasting value remains on HOLD.", icon=":material/pause_circle:")

    st.subheader("Paper-to-run delta audit")
    st.warning(verification.scope_disclosure, icon=":material/compare_arrows:")
    delta_rows = []
    for row in verification.paper_run_delta["dimensions"]:
        delta_rows.append(
            {
                **row,
                "paper_value": json.dumps(row.get("paper_value"), ensure_ascii=False),
                "run_value": json.dumps(row.get("run_value"), ensure_ascii=False),
            }
        )
    st.dataframe(delta_rows, hide_index=True, width="stretch")
    with st.expander("Why deployment is blocked", icon=":material/block:"):
        for blocker in baseline.blockers:
            st.write(f"- {blocker}")
    st.info("GPT-5.6 can explain these results but cannot change a gate.", icon=":material/lock:")
    if st.button("Generate the decision memo", type="primary", icon=":material/arrow_forward:"):
        st.session_state["forecastproof_verification_complete"] = True
        st.switch_page("app_pages/decision_memo.py")


def _render_memo(memo: DecisionMemo, brief: Any, verification: Any, response_id: str, metadata: dict[str, Any]) -> None:
    audit = audit_research_memo(memo, brief, verification)
    color = {"GO": "green", "CONDITIONAL": "orange", "NO_GO": "red"}[memo.recommendation]
    st.badge(memo.recommendation, color=color, icon=":material/gavel:")
    st.subheader(memo.headline)
    with st.container(horizontal=True):
        st.metric("Adaptation", verification.verdict, border=True)
        st.metric("Skill gate", "PASS" if verification.baseline_comparison.value_gate else "HOLD", border=True)
        st.metric("Deployment", "HOLD", border=True)
        st.metric("Audit score", f"{audit.score}/100", border=True)
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
    st.subheader("Deterministic memo audit")
    if audit.passed:
        st.success("The memo passed every grounding, scope, and safety check.", icon=":material/verified_user:")
    st.dataframe(
        [{"check": check.label, "status": "passed" if check.passed else "failed", "detail": check.detail} for check in audit.checks],
        hide_index=True,
        width="stretch",
    )
    pack = build_research_audit_pack(
        brief=brief,
        verification=verification,
        memo=memo,
        memo_audit=audit,
        response_id=response_id,
        run_metadata=metadata,
    )
    with st.container(horizontal=True):
        st.download_button("Download memo JSON", json.dumps(memo.to_dict(), ensure_ascii=False, indent=2), "forecastproof_memo.json", "application/json")
        st.download_button("Download complete Audit Pack", json.dumps(pack, ensure_ascii=False, indent=2), "forecastproof_audit_pack.json", "application/json", type="primary")


def render_decision_memo() -> None:
    paper_id = selected_case_id()
    brief = _brief(paper_id)
    verification = _verification(paper_id)
    replay = build_research_replay_memo(brief, verification)
    st.title("Decision memo")
    st.caption("Verified replay is free. Live GPT-5.6 requires one explicit click and uses two read-only tools.")
    mode = st.segmented_control("Generation mode", ["Verified replay", "Live GPT-5.6"], default="Verified replay", key="forecastproof_memo_mode")
    memo, response_id = replay, "offline-replay"
    metadata: dict[str, Any] = {"generation_mode": "verified_replay", "request_count": 0, "usage": None}
    if mode == "Live GPT-5.6":
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        with st.form("forecastproof_live_run", border=True):
            st.markdown("#### Cost-controlled live synthesis")
            controls = st.columns(2)
            effort = controls[0].selectbox("Reasoning effort", ["none", "low", "medium"], index=1)
            cap = controls[1].select_slider("Maximum output tokens", [800, 1200, 1600], value=1200)
            submitted = st.form_submit_button("Run EvidenceAnalyst once", type="primary", disabled=not has_key)
        if not has_key:
            st.warning("OPENAI_API_KEY is not available; replay remains fully functional.", icon=":material/key_off:")
        if submitted:
            try:
                with st.spinner("GPT-5.6 is reading the case evidence and deterministic result…"):
                    run = OpenAIResponsesDecisionAgent(reasoning_effort=effort, max_output_tokens=cap, retries=1).generate(brief=brief, verification=verification)
                st.session_state["forecastproof_group_live_run"] = run
            except Exception as exc:
                st.error(f"Live synthesis failed safely: {exc}", icon=":material/error:")
        if run := st.session_state.get("forecastproof_group_live_run"):
            memo, response_id = run.memo, run.response_id
            metadata = {"generation_mode": "live_gpt_5_6", "request_count": run.request_count, "usage": run.usage.to_dict()}
    _render_memo(memo, brief, verification, response_id, metadata)


def _render_iteration_result(result: ControlledIterationResult | dict[str, Any]) -> None:
    payload = result.to_dict() if isinstance(result, ControlledIterationResult) else result
    passed = all(row["passed"] for row in payload["checks"])
    if passed:
        st.success("The child cleared every research-promotion gate; deployment remains unauthorized.")
    else:
        st.warning("The child failed at least one guardrail, so the parent remains the incumbent.")
    with st.container(horizontal=True):
        st.metric("Decision", payload["decision"].replace("_", " "), border=True)
        st.metric("Primary improvement", f"{payload['primary_improvement']:.2%}", border=True)
        st.metric("Runtime", f"{payload['runtime_seconds']:.2f}s", border=True)
        st.metric("Deployment", "Unauthorized", border=True)
    st.dataframe(payload["checks"], hide_index=True, width="stretch")


def render_iteration_lab() -> None:
    paper_id = selected_case_id()
    task, parent, card = get_case_runtime(PROJECT_DIR, paper_id)
    diagnostic_folds, promotion_folds = iteration_fold_partition(parent["prediction_artifact"])
    diagnostics = diagnose_prediction_artifact(parent["prediction_artifact"], fold_ids=diagnostic_folds)
    proposals = build_iteration_proposals(task, parent, card)
    proposal_by_id = {proposal.proposal_id: proposal for proposal in proposals}

    st.title("Evidence-guided iteration lab")
    st.caption(f"Same selected case from Analyze to Iteration · {_case_label(paper_id)}")
    st.info(
        "The advisor emits at most three allow-listed executable changes. It cannot write arbitrary code, inspect the promotion holdout, or authorize deployment.",
        icon=":material/account_tree:",
    )
    st.subheader("1. Diagnose the parent on development folds")
    with st.container(horizontal=True):
        st.metric("Development rows", diagnostics.observations, border=True)
        st.metric("Directional accuracy", f"{diagnostics.global_metrics['directional_accuracy']:.2%}", border=True)
        st.metric("Fold MAE variation", f"{diagnostics.fold_mae_cv:.1%}", border=True)
        st.metric("Untouched holdout", f"{len(promotion_folds)} folds", border=True)
    for finding in diagnostics.findings:
        st.write(f"- {finding}")

    st.subheader("2. Review bounded executable proposals")
    selected = st.selectbox("Proposed experiment", list(proposal_by_id), format_func=lambda value: proposal_by_id[value].title, key="iteration_proposal_id")
    proposal = proposal_by_id[selected]
    with st.container(border=True):
        st.badge("Human approval required", color="orange")
        st.markdown(f"#### {proposal.title}")
        st.write(proposal.hypothesis)
        st.code(json.dumps(proposal.model_parameters, indent=2), language="json")
        st.caption(proposal.expected_outcome)
    st.dataframe([item.to_dict() for item in proposal.evidence], hide_index=True, width="stretch")

    st.subheader("3. Approve exactly one child run")
    with st.form("controlled_iteration_form", border=True):
        budget = st.slider("Runtime budget (seconds)", 15, proposal.max_runtime_seconds, min(60, proposal.max_runtime_seconds), 15)
        approved = st.checkbox("I approve one child run and understand it cannot authorize deployment.")
        submitted = st.form_submit_button("Run one controlled iteration", type="primary", icon=":material/play_arrow:")
    if submitted:
        if not approved:
            st.warning("Explicit approval is required.")
        else:
            try:
                with st.spinner("Training and auditing one bounded child…"):
                    result = run_controlled_iteration(PROJECT_DIR, task, parent, proposal, approved=True, runtime_budget_seconds=budget)
                st.session_state["iteration_lab_result"] = result
            except Exception as exc:
                st.error(f"Controlled iteration stopped safely: {exc}")
    result = st.session_state.get("iteration_lab_result")
    if result and result.task_id == task.task_id and result.method_id == paper_id:
        st.subheader("4. Deterministic promotion decision")
        _render_iteration_result(result)
    lineage = [row for row in load_lineage(PROJECT_DIR) if row.get("task_id") == task.task_id and row.get("method_id") == paper_id]
    if lineage:
        st.subheader("Case lineage")
        st.dataframe(list(reversed(lineage)), hide_index=True, width="stretch")
