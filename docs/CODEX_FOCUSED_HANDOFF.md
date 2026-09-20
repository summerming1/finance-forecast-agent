# Codex development handoff — Mission Research line

> Status: APPROVED under ADR-FOCUS-001, ADR-MISSION-002 and ADR-MISSION-PRODUCT-003.

## 1. Start every Codex session with a read-only audit

Read AGENTS.md and the mandatory documents listed there, then inspect branch/HEAD/status. Do not stash/reset user work automatically and do not infer implementation from roadmap names.

Repository: `summerming1/finance-forecast-agent`
Authoritative work branch: `feat/mission-research-v2`

## 2. Current verified milestone

V1.1 remains a permanent regression gate.
**PR-1 / V2-A Evidence Foundation is implemented and targeted acceptance passed.**
The next implementation milestone is **PR-2 / V2-A Mission + Research Workspace**.

PR-1 delivered:
- execution status / research outcome separation;
- row-level PredictionArtifact and recomputable metrics;
- train-only zero/mean/median naive baselines plus existing Ridge/RF/GBDT;
- actual ExecutionManifest;
- real parent→child config diff;
- deterministic StructuredFeedback;
- Exposure Ledger v0;
- batch-plan freeze and fact-time focused events.

Do not reimplement PR-1 unless a regression requires it.

## 3. Approved gated sequence

```text
PR-1 / V2-A  Evidence Foundation                         COMPLETE
PR-2 / V2-A  Mission + Research Workspace                NEXT
PR-3 / V2-B  Adaptive Research + Agent Value Benchmark   PLANNED
PR-4 / V2-B  Persistent Execution + ResearchPackage      PLANNED
PR-5 / V2.1  Memory + Confirmation + ModelBundle         PLANNED
PR-6 / V2.2  Controlled BYO Data/Model Pilot             PLANNED
V3           Shadow Forecasting                           LATER
```

Do not start a later PR until the previous PR's new tests and all affected cumulative regressions pass.

## 4. PR-2 scope

Mission stays thin: user question/type and Task/Campaign references only. Do not duplicate label/data/budget/runtime state.
Build the product flow around Create → Overview → Research history/tree → Candidate detail. Research Tree is a projection of recorded facts, not a graph runtime. Low-level paths/fixture settings belong in advanced settings. Unsupported natural-language tasks must be rejected rather than silently mapped to SPY.

## 5. Later boundaries

PR-3 must prove feedback/evidence can affect research decisions and implement a matched-budget Random/TPE/One-shot/Adaptive Agent benchmark. Fixture success is not Agent value proof.

PR-4 reuses LocalTaskQueue for persistent attempts/idempotency/recovery/cancel and completes ResearchPackage. Do not create another queue/controller.

PR-5 reuses ExperimentMemory as a compatibility-filtered weak prior, adds confirmation isolation and explicit refit ModelBundle.

PR-6 accepts only controlled same-task external data and reviewed local adapters. No arbitrary Python/notebook/pickle/Docker execution. Controlled BYO precedes full Shadow Forecasting.

## 6. Testing and claims

Use `docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md` as the acceptance contract. Keep focused/unit, integration/recovery, UI, live LLM, external/native and commercial-value evidence separate.

Synthetic data/users and assistant-authored fixtures are engineering evidence only and must be labeled. Never use focused CI to claim historical native training, live scientific quality, independent confirmation, Agent superiority, or customer demand.

## 7. Documentation rule

`CURRENT_IMPLEMENTATION.md` describes only verified current behavior. Roadmap/ADR describe approved future direction. Update the V2 release record for each completed PR, preserve historical acceptance records, and report exact commands/results plus untested boundaries.
