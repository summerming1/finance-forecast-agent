from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget

st.set_page_config(page_title="Focused SPY Research", layout="wide")
st.title("Focused SPY Daily Research")
st.caption("F0 + F1: one task, controlled research loop, development-only evidence. No trading or profitability claim.")

project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
raw_path = Path(st.text_input("Frozen SPY Yahoo JSON", "inputs/spy_chart_2010_2025.json"))
source_meta_text = st.text_input("Source metadata JSON (optional)", "inputs/spy_source.json")
source_meta = Path(source_meta_text) if source_meta_text else None
advisor_mode = st.selectbox("Iteration suggestion source", ["deterministic", "replay", "live"], index=0)
fixture_dir = st.text_input("Focused LLM fixtures", "projects/finance_agent/llm_fixtures_focused")

st.subheader("Task contract")
st.json(FocusedTaskSpec().to_dict())
st.warning("The existing SPY history is treated as historical development data. This page does not claim an independent blind final test.")

if raw_path.exists():
    try:
        frame, snapshot = build_spy_daily_research_frame(raw_path, source_metadata_path=source_meta)
        cols = st.columns(5)
        cols[0].metric("Rows", snapshot.row_count)
        cols[1].metric("Start", snapshot.start_date)
        cols[2].metric("End", snapshot.end_date)
        cols[3].metric("Exposure", snapshot.exposure)
        cols[4].metric("Dataset hash", snapshot.semantic_fingerprint)
        with st.expander("Dataset snapshot"):
            st.json(snapshot.to_dict())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        st.error(f"Dataset validation failed: {exc}")
        frame = None
        snapshot = None
else:
    st.info("Provide the frozen SPY Yahoo JSON to run a campaign. No synthetic fallback is used.")
    frame = None
    snapshot = None

with st.form("focused_campaign_form"):
    rounds = st.number_input("Max research rounds", min_value=1, max_value=5, value=3)
    candidates = st.number_input("Max new candidates per round", min_value=1, max_value=3, value=2)
    max_fit_calls = st.number_input("Max fit calls", min_value=10, max_value=100, value=40)
    run = st.form_submit_button("Run focused campaign", disabled=frame is None)

if run and frame is not None and snapshot is not None:
    budget = ResearchBudget(max_rounds=int(rounds), max_new_candidates_per_round=int(candidates), max_fit_calls=int(max_fit_calls))
    try:
        with st.spinner("Running frozen baselines and research rounds..."):
            result = FocusedResearchController(
                project_dir=project_dir,
                task=FocusedTaskSpec(),
                dataset=snapshot,
                frame=frame,
                budget=budget,
                advisor_mode=advisor_mode,
                fixture_dir=fixture_dir,
            ).run()
        st.success(f"Campaign finished: {result['terminal_status']}")
        st.subheader("Research conclusion")
        a, b, c = st.columns(3)
        a.metric("Best baseline", result["best_baseline_candidate_id"])
        b.metric("Best candidate", result["best_candidate_id"])
        c.metric("Confirmation", result["confirmation_status"])
        st.subheader("Frozen baselines")
        st.dataframe([
            {"candidate_id": row["candidate"]["candidate_id"], "model": row["candidate"]["model_family"], "features": ", ".join(row["candidate"]["feature_groups"]), "MAE": row["metrics"]["mae"], "RMSE": row["metrics"]["rmse"], "directional_accuracy": row["metrics"]["directional_accuracy"]}
            for row in result["baseline_results"]
        ], use_container_width=True, hide_index=True)
        st.subheader("What generated each model-iteration suggestion?")
        for round_row in result["rounds"]:
            st.markdown(f"### Round {round_row['round_index']} · source: `{round_row['advisor_source']}`")
            for item in round_row["items"]:
                hyp = item["hypothesis"]
                st.markdown(f"**Hypothesis:** {hyp['statement']}")
                st.caption(f"Mechanism: {hyp['mechanism']} · Evidence: {', '.join(hyp['evidence_refs']) or 'none'}")
                if item.get("result"):
                    row = item["result"]
                    st.write({
                        "actual_model": row["candidate"]["model_family"],
                        "actual_features": row["actual_features"],
                        "actual_estimator_params": row["estimator_params"],
                        "metrics": row["metrics"],
                        "research_verdict": row["research_verdict"],
                        "relative_mae_vs_best_baseline": row["relative_mae_vs_best_baseline"],
                    })
                else:
                    st.write({"status": item["status"], "candidate": item["candidate"]})
        with st.expander("Raw campaign JSON"):
            st.json(result)
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        st.error(str(exc))

st.divider()
st.subheader("Previous focused campaigns")
root = project_dir / "focused_campaigns"
rows = []
if root.exists():
    for path in sorted(root.glob("*/campaign.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append({"campaign_id": payload["campaign"]["campaign_id"], "status": payload["terminal_status"], "best_candidate": payload["best_candidate_id"], "advisor_mode": payload["campaign"]["advisor_mode"], "confirmation": payload["confirmation_status"]})
        except (ValueError, KeyError, OSError, json.JSONDecodeError):
            continue
if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.caption("No focused campaign artifacts yet.")
