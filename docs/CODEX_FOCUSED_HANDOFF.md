# Codex development handoff — Mission Research line

> Status: APPROVED under ADR-FOCUS-001 and ADR-MISSION-002.

## 1. Start every Codex session with a read-only audit

Read AGENTS.md and the mandatory documents listed there. Then:

```powershell
git status --short
git fetch origin
git branch --show-current
git log -1 --oneline
git log -1 --oneline origin/feat/p1-focused-us-equity-loop-v1
```

Do not stash/reset user work automatically.

## 2. Branch and milestone

Repository: `summerming1/finance-forecast-agent`.

Validated base: `feat/p1-focused-us-equity-loop-v1`.

Current work branch: `feat/mission-research-v2`.

**V1.1 reliability is complete and is now a permanent regression gate. The next implementation milestone is V2-A.**

## 3. Completed V1.1 implementation (do not redo unless a regression requires it)

1. add negative tests for adjusted-close, XNYS session completeness, short history/split overlap, low baseline budget, parameter bounds and development verdict;
2. introduce one shared focused split/evaluation policy source instead of duplicating thresholds;
3. require adjusted close; no close fallback;
4. align minimum supervised rows with split requirements and reject overlapping test folds;
5. check baseline fit budget before any fit;
6. validate numeric parameter ranges before model construction;
7. reserve candidate fit budget before execution and record failure in the round;
8. rename successful development threshold semantics to `development_screen_passed` (keep legacy field only for compatibility);
9. update focused Streamlit width API and preflight messaging;
10. run focused tests, Ruff, compileall, and branch CI on Python 3.11/3.13;
11. update P1_FOCUS_F0_F1 and CURRENT_IMPLEMENTATION with actual results.

V1.1 intentionally did not implement Mission UI, QQQ, LSTM, long-term Memory or automatic literature retrieval. Do not reopen those scopes while fixing V1.1 regressions.

## 4. Current next work: V2 implementation sequence

### V2-A
Thin Mission; EvaluationPolicy; row-level PredictionArtifact/Manifest; naive baselines; deterministic FeedbackBuilder; ResearchPackage skeleton.

### V2-B
Persistent queue/attempt/idempotency/recovery; Evidence-grounded live-record/replay Advisor; reviewed MethodCard evidence in ContextBuilder; literature/experiment citation gate; ResearchPackage complete.

### V2.1
Existing ExperimentMemory read/write; exposure/confirmation gates; explicit refit; loadable ModelBundle.

Do not create second Controller/Queue/Memory/Evaluator.

## 5. Literature implementation rule

Next V2 does not begin by building a crawler.

First prove that 1–3 reviewed MethodCards materially participate in research:
- mechanism/condition evidence is visible in ContextBuilder;
- hypotheses cite stable evidence IDs;
- compiler validates cited evidence;
- later rounds combine paper evidence with actual experiment feedback;
- local results never mutate paper facts;
- applicability mismatches are shown.

Only after this is useful should bounded automatic literature retrieval be added.

## 6. Testing and claims

Use `docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md` as the acceptance contract.

Separate:
- focused deterministic/unit/integration;
- UI AppTest/manual browser;
- live LLM;
- external/native paper environments.

Never use a focused green CI badge to claim all historical native reproduction was rerun.

## 7. When to ask the user

Ask before:
- changing SPY/daily/next-return primary scope;
- changing primary metric or confirmation policy;
- adding trading/profitability claims;
- replacing the runtime with RD-Agent/DeepSeek/LangGraph/etc.;
- opening arbitrary code execution;
- changing the roadmap milestone order.

For a pure bug fix inside the approved milestone, proceed and update current docs.

## 8. Approved sequential delivery override (2026-09-20)

ADR-MISSION-003 authorizes PR-0 through PR-6 in order, with `scripts/check_mission_gate.py` between stages. Preserve prior user work. Engineering acceptance may use explicitly tagged simulated data and assistant-authored fixtures; these do not satisfy live-provider, scientific or user-value acceptance. See `MISSION_PR_SERIES_20260920.md` before inferring current completion.
