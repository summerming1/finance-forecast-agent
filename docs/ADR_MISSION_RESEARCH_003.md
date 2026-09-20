# ADR-MISSION-003: sequential product delivery and evidence boundaries

- Status: accepted by the user on 2026-09-20.
- Supersedes only the delivery ordering in ADR-MISSION-002, not its scientific invariants.
- Original base: `571beb91ad8911cdb540192f6a0543755da6edb6`.
- Delivery: PR-0 through PR-6; each stage must pass its local gate before the next starts.

## Approved sequence

| Stage | Scope | Capability milestone |
|---|---|---|
| PR-0 | Decision, contracts and repeatable regression gate | Delivery contract |
| PR-1 | Row predictions, manifests, naive baselines, feedback, exposure and terminal semantics | V2-A evidence |
| PR-2 | Thin Mission and a workspace projection of the existing controller | V2-A product entry |
| PR-3 | Feedback-grounded proposals, reviewed evidence and four-arm value benchmark | V2-B research |
| PR-4 | Existing LocalTaskQueue, attempts, idempotency, recovery and research packages | V2-B reliability |
| PR-5 | Existing ExperimentMemory, confirmation gate and explicit refit bundle | V2.1 engineering |
| PR-6 | Contracted SPY data and a reviewed local model adapter | V2.2 pilot infrastructure |

BYO pilot infrastructure precedes the full Shadow product. User research can run in parallel, but simulated users cannot satisfy commercial acceptance. Full V2.2 acceptance still needs a real user's task and review. V3 remains immutable forward forecasting, not trading.

## No new parallel engine

Mission stores only the question, supported template and Task/Campaign links. Reuse ResearchController, LocalTaskQueue, PredictionArtifact, MethodAdapter and ExperimentMemory. Literature facts, local observations and model inferences stay separate. LLMs do not decide labels, splits, metrics, permissions or confirmation.

## Four separate acceptance axes

1. Engineering: actual execution, reproducible metrics, budgets, recovery and negative tests.
2. Research value: common-space random / Bayesian / one-shot / adaptive comparison, with attempts and costs recorded.
3. Scientific evidence: development, robustness, confirmation and prospective evidence are separate.
4. Product/commercial: a real non-author user completes and reviews a task; usability or payment is not inferred from CI.

## Test provenance approved for this batch

The user permits explicit simulation datasets and assistant-authored LLM responses to test contracts and workflow. Such fixtures must carry `simulation_only` and `assistant_authored_fixture` provenance. A replay or mocked provider request is not a live provider call and proves no prediction advantage, user time saving, blind evaluation or payment. Missing real acceptance is reported as pending, never fabricated.

## Permanent restrictions

Keep SPY / daily / next-session adjusted-close return / MAE / forecast-only. Do not open arbitrary code or pickle uploads, change the runtime, add autonomous trading, or claim broad research tasks. Unknown external exposure is not eligible for independent confirmation. Engineering failure is not scientific evidence of no improvement. Failed/interrupted work does not restore free research budget.

## Shipping policy

Keep the original branch intact. Publish stacked reviewable PRs, with exact base/head identifiers and test commands. Do not auto-merge. Each stage records its tested scope, skipped real/live/native checks and rollback boundary in `MISSION_PR_SERIES_20260920.md`. A green test suite is not a market or scientific success gate.
