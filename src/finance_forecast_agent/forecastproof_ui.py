from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

from .forecastproof import DecisionMemo, build_replay_memo, load_demo_brief, verify_demo_claim
from .openai_responses import OpenAIResponsesDecisionAgent


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
        "The verified demo works without an API key; live mode uses GPT-5.6."
    )
    st.markdown(":green-badge[Verified sample] :blue-badge[GPT-5.6 live mode] :gray-badge[Research use only]")

    metrics = st.columns(4)
    metrics[0].metric("Evidence spans", verification.evidence_span_count)
    metrics[1].metric("Deterministic gates", f"{verification.gates_passed}/4")
    metrics[2].metric("Paper MSE", f"{verification.reported_metrics['mse']:.3f}")
    metrics[3].metric("Local MSE", f"{verification.local_metrics['mse']:.6f}")

    st.subheader("One claim. Three auditable steps.")
    steps = st.columns(3)
    with steps[0].container(border=True):
        st.markdown(":material/article:")
        st.markdown("#### 1. Analyze")
        st.write("Extract the claim, protocol, unknowns, and source-revision evidence from a verified MethodCard.")
    with steps[1].container(border=True):
        st.markdown(":material/fact_check:")
        st.markdown("#### 2. Verify")
        st.write("Replay deterministic evidence, protocol, dataset, and metric gates against a native-run artifact.")
    with steps[2].container(border=True):
        st.markdown(":material/description:")
        st.markdown("#### 3. Decide")
        st.write("Generate a cited decision memo that separates reproduced facts from deployment risks.")

    st.page_link(
        "app_pages/analyze.py",
        label="Start the 3-minute verified demo",
        icon=":material/play_arrow:",
    )

    with st.container(border=True):
        st.markdown("#### The demo question")
        st.write(brief.claim)
        st.caption(f"{brief.title} · {brief.dataset} · {brief.horizon}")

    st.subheader("Why ForecastProof")
    st.markdown(
        """
- **Research claims become inspectable objects.** Every protocol field points back to a pinned source revision.
- **The model does not grade its own work.** Deterministic code decides whether evidence, protocol, data, and metrics pass.
- **The output is decision-shaped.** Teams get a cited memo with facts, risks, actions, and an explicit guardrail.
"""
    )


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
    if mode == "Live GPT-5.6":
        has_key = bool(os.getenv("OPENAI_API_KEY"))
        if not has_key:
            st.warning(
                "Set OPENAI_API_KEY to run the live Responses agent. The verified replay remains visible below.",
                icon=":material/key_off:",
            )
        if st.button(
            "Run EvidenceAnalyst",
            type="primary",
            icon=":material/auto_awesome:",
            disabled=not has_key,
        ):
            try:
                with st.spinner("GPT-5.6 is inspecting the evidence and verification tools…"):
                    run = OpenAIResponsesDecisionAgent().generate(brief=brief, verification=verification)
                st.session_state["forecastproof_live_memo"] = run.memo
                st.session_state["forecastproof_live_response_id"] = run.response_id
                st.toast("Live decision memo generated", icon=":material/check_circle:")
            except Exception as exc:
                st.error(f"Live mode failed safely: {exc}", icon=":material/error:")
        if live_memo := st.session_state.get("forecastproof_live_memo"):
            memo = live_memo
            response_id = st.session_state.get("forecastproof_live_response_id", "unknown")

    _render_memo(memo, response_id=response_id)


def _render_memo(memo: DecisionMemo, *, response_id: str) -> None:
    color = {"GO": "green", "CONDITIONAL": "orange", "NO_GO": "red"}[memo.recommendation]
    st.badge(memo.recommendation, color=color, icon=":material/gavel:")
    st.subheader(memo.headline)
    st.metric("Decision confidence", f"{memo.confidence:.0%}")

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
    with st.expander("Agent trace and citations", icon=":material/account_tree:"):
        st.caption(f"Mode: {memo.mode} · Model: {memo.model} · Response: {response_id}")
        st.write(" → ".join(memo.tool_trace))
        st.dataframe(list(memo.citations), hide_index=True, width="stretch")

    payload = json.dumps(memo.to_dict(), ensure_ascii=False, indent=2)
    st.download_button(
        "Download memo JSON",
        data=payload,
        file_name="forecastproof_decision_memo.json",
        mime="application/json",
        icon=":material/download:",
    )


def render_research_lab() -> None:
    from .streamlit_p09 import render_app

    st.caption("Advanced workspace · the original seven-stage research control tower")
    render_app(embedded=True)
