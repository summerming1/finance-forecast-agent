# ForecastProof — Build Week submission brief

> Code status: v0.6 golden path, three-paper S&P 500 suite, deterministic audits, cost controls, Audit Pack, controlled iteration, and automated tests are implemented. Public deployment, screenshots, final video, eligibility confirmation, and Devpost fields remain submission tasks.

## One-line pitch

ForecastProof is an evidence agent that turns forecasting papers into comparable, statistically challenged research decisions—and refuses to promote a model when the evidence is not strong enough.

## Problem

A forecasting paper can look promising while hiding practical uncertainty across data revisions, label definitions, temporal leakage, baseline selection, and missing protocol details. A polished LLM summary does not solve that trust problem. Research teams need a system that distinguishes:

- what the paper actually supports;
- whether a method can run under a shared executable contract;
- whether it beats a simple leakage-safe baseline with statistical evidence;
- whether the next model change really ran and earned promotion.

## What ForecastProof does

The judge-facing flow contains three evidence-backed S&P-related papers. Their Random Forest, GBDT, and LSTM method branches run on one frozen SPY next-day-direction task with identical 12-lag features, 41 purged walk-forward folds, 656 out-of-fold targets, and a fold-train-only majority baseline.

```text
Select paper
  → inspect pinned evidence and unknowns
  → disclose every paper-to-run adaptation
  → verify frozen data, common protocol, and aligned artifacts
  → challenge accuracy with baseline + Wilson interval + binomial test
  → generate an audited GPT-5.6 / replay decision memo
  → approve one allow-listed child training run
  → promote or retain on later untouched folds
```

All three cases pass the four adaptation-integrity gates. None passes the statistical skill gate, so deployment stays on HOLD. This is deliberate and visible. ForecastProof does not call these three runs strict reproductions; the underlying research harness keeps strict reproduction as a separate tier.

## Why it is agentic

GPT-5.6 EvidenceAnalyst uses the Responses API and must call two read-only tools:

- `get_evidence_brief`
- `get_verification_result`

It returns a strict DecisionMemo structured output containing verified facts, rationale, risks, actions, citations, confidence, and a research-only guardrail. Its memo then faces eight deterministic checks: decision authority, tool grounding, citation validity, evidence coverage, completeness, research safety, adaptation-scope honesty, and baseline/statistical honesty.

The model owns synthesis, not truth. It cannot change a gate, hide a HOLD result, label an adaptation as strict reproduction, authorize trading, or launch training.

Iteration proposals bind two evidence types—paper evidence and observed development-fold diagnostics—to allow-listed model parameters. Human approval launches exactly one real child. Later folds were reserved before diagnosis, and deterministic primary, secondary, slice, runtime, finiteness, and comparison-integrity gates decide promotion.

## Frozen results

| Case | Model | Accuracy | Lift vs 49.24% baseline | Adaptation | Skill |
|---|---|---:|---:|---|---|
| `arxiv_2004_10178v2` | RF | 51.22% | +1.98% | 4/4 PASS | HOLD |
| `arxiv_2108_10826` | GBDT | 51.68% | +2.44% | 4/4 PASS | HOLD |
| `arxiv_2501_17366` | LSTM | 47.71% | −1.52% | 4/4 PASS | HOLD |

The first bounded child for every model family also runs end to end. RF and LSTM improve the holdout point estimate but fail slice/secondary guardrails; GBDT regresses and fails three gates. Every parent is retained and deployment remains unauthorized.

## Cost and reliability

- Verified replay is the default and needs no API key.
- Live mode runs only after one explicit form submission.
- Default live settings: low reasoning, 1,200 output-token cap, one attempt, `store=false`.
- Usage telemetry records request and token counts without storing the API key.
- Build and test workflows use replay/mock only and spend no Luna credits.
- A live failure never removes the audited offline result.

The final v0.6 live Luna acceptance used the GBDT case, low reasoning, and a 1,200-token cap. It called both tools, returned CONDITIONAL with the failed skill gate and deployment HOLD, and passed all eight memo checks at 100/100. The two-request loop used 4,104 total tokens; the list-rate reference was approximately `$0.009324` and compatible-provider billing may differ.

## How we used Codex

Codex helped audit the research harness, isolate hackathon work in a dedicated clone and branch, design the S&P 500 common-task contract, implement the Streamlit product flow and Responses tool loop, build tests that really train all three model families, and keep the scope disclosure honest. The pre-event baseline is commit `ffa048e`; the Build Week work is recorded on `codex/openai-build-week`.

## Challenges

The hardest decision was refusing two tempting shortcuts: calling a common benchmark a paper reproduction, and treating a better accuracy point estimate as established skill. We also rejected a fourth candidate from the golden path because its local MethodCard had an empty evidence quote. Fewer trustworthy cases made a stronger product than a larger unsupported claim.

## What's next

1. Add an independent frozen out-of-period SPY regime.
2. Add paired parent-child confidence intervals or McNemar/paired-bootstrap promotion evidence.
3. Add pre-registered multi-seed evaluation.
4. Route uploaded papers to strict, adaptation, or blocked paths with a visible compatibility explanation.
5. Add user-provided US-equity data mapping and cost-aware economic validation only after forecast skill passes.

## Suggested 3-minute demo

1. Home: show three papers, three model families, 656 identical rows, and integrity PASS.
2. Analyze: select the GBDT case; show original scope versus shared task and two evidence spans.
3. Verify: show four gates, +2.44% point lift, statistical HOLD, and paper-to-run delta.
4. Decision memo: show CONDITIONAL, 100/100 audit, tool grounding, and Audit Pack.
5. Iteration: show allow-listed parameters, approval, a real retained-parent result, and deployment unauthorized.

## Submission checklist

- [ ] Deploy a public Streamlit URL and test it in a clean browser.
- [ ] Record a 2:30–3:00 minute English demo using `BUILD_WEEK_DEMO_SCRIPT.md`.
- [ ] Capture four screenshots: multi-paper Home, Verify statistics, audited memo, retained-parent iteration.
- [ ] Add public repository and demo URLs to Devpost.
- [ ] Confirm `codex/openai-build-week` and build-period evidence are visible.
- [ ] Test replay without a key and live GPT-5.6 once in the deployed environment.
- [ ] Confirm no `.env`, key, private endpoint, or user data appears in the video or repository.
- [ ] Include the research-only / not-investment-advice statement.

## Official references

- [OpenAI Build Week](https://openai.com/zh-Hans-CN/build-week/)
- [Responses API migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Function calling guide](https://developers.openai.com/api/docs/guides/function-calling)
- [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
