# ForecastProof — three-minute demo script

## Before recording

- Use a clean browser window at 1440×900 or 1920×1080.
- Start on Home with the app already warm.
- Keep `Verified replay` as the reliable path.
- Configure live GPT-5.6 only if the deployed key and quota have been tested.
- Do not show `.env`, terminals containing keys, or local absolute paths.

## 0:00–0:20 — Problem and promise

**Say:**

> Forecasting teams can find exciting paper results in minutes, but it can take days to learn whether the claim is reproducible and useful. ForecastProof turns one paper claim into an auditable research decision.

**Show:** Home title, four metrics, and the three-step flow.

## 0:20–0:55 — Analyze

Open **Analyze**.

**Say:**

> The demo begins with a strict DLinear claim on the Exchange-Rate benchmark. ForecastProof does not rely on a loose summary: the MethodCard binds the result, data split, scaling, hyperparameters, and unknowns to pinned paper and repository evidence.

Expand one `reported results` span and one protocol span. Point to the source revision.

## 0:55–1:35 — Verify

Open **Verify**.

**Say:**

> The model does not grade itself. Deterministic code checks four things: evidence approval, protocol fidelity, dataset hash, and metric tolerance. All four pass. The paper reports MSE 0.081; our native run produced 0.0810795, inside the declared tolerance.

Show the bar chart, the four gates, and the audit identifiers. State that this is a frozen artifact replay, not fake instant training.

## 1:35–2:25 — Decide and audit with GPT-5.6

Open **Decision memo**.

**Say:**

> GPT-5.6 is the EvidenceAnalyst. Through the Responses API it must call the evidence brief and verification result tools before returning this strict structured memo. The memo separates verified facts from risks and actions.

Show `Verified replay` first and point to the deterministic 100/100 memo audit. If live mode is tested, switch to **Live GPT-5.6**, keep low reasoning and the 1,600-token cap, run it once, then expand **Agent trace and citations** to show the two tools and token/cost telemetry.

Point to the recommendation and guardrail, then show the complete Audit Pack download.

## 2:25–2:45 — Product depth

Open **Research lab** briefly.

**Say:**

> Behind the three-minute product flow is the original seven-stage research harness: literature, data, MethodCard review, reproduction configuration, native runs, benchmarks, and audit. We kept that depth while removing it from the judge's golden path.

## 2:45–3:00 — Build evidence and close

Return to Home or Decision memo.

**Say:**

> The pre-event baseline is commit ffa048e. Our during-event diff, Codex task history, and dedicated Build Week branch document the new work. ForecastProof helps teams move faster without confusing a reproduced metric with investment advice.

## Recording fallback

If live GPT-5.6 fails during recording, stay in verified replay mode and show the mocked Responses integration test in the repository afterward. Do not spend the demo waiting on an API call.
