# Focused / Mission Research Acceptance Plan

> Status: APPROVED. Tests are divided by milestone. Passing one layer never implies all historical native or live-LLM work was rerun.

## 1. Acceptance categories

1. Engineering: execution is real, bounded, recoverable and auditable.
2. Research-process: hypotheses map to real experiments and results can change later actions.
3. Scientific evidence: development, robustness, confirmation and strict reproduction are not conflated.
4. Product: a non-author can create a supported task, run it, understand it, and take away the result.

## 2. V1.1 reliability gate

The next implementation milestone must pass these focused negative/compatibility cases.

| ID | Scenario | Required behavior |
|---|---|---|
| R01 | adjusted close missing but close exists | fail closed; never label close as adjusted close |
| R02 | symbol != SPY | fail before artifact creation |
| R03 | missing XNYS session inside the source period | fail with explicit session-gap error |
| R04 | future observation perturbed | earlier feature values remain unchanged |
| R05 | dataset too short for declared split | fail preflight; no overlapping/duplicate test-row weighting silently accepted |
| R06 | normal long dataset | all test folds are ordered, in bounds and pairwise non-overlapping |
| R07 | baseline requires 12 fits, budget=10 | fail before any model fit |
| R08 | invalid/unsafe model parameter values | fail before estimator training |
| R09 | unknown model/feature group | fail; no proxy/fallback |
| R10 | candidate fit fails after reservation | failure recorded; reserved budget is not restored as free research budget |
| R11 | development candidate crosses threshold | label as development screen only; not confirmed/promoted |
| R12 | historical SPY data | confirmation remains not-run/exposed |
| R13 | same content moved to a different path | semantic identity unchanged |
| R14 | content changes at same path | data/task fingerprint changes |
| R15 | Streamlit focused page | no deprecated use_container_width in the focused page; current supported width API renders |

Focused compatibility:
- user-reported 4002-row Yahoo SPY path remains supported;
- deterministic campaign can still end `completed_no_improvement`;
- Python 3.11 CI plus Python 3.13 focused CI are both targeted where dependencies support them.

## 3. V2-A task/evidence gate

- thin Mission links to Task/Campaign without duplicating contract state;
- frozen EvaluationPolicy is separate from ResearchBudget;
- zero/mean/median plus Ridge/RF/GBDT baselines are fit using training-fold information only;
- every candidate writes a row-level PredictionArtifact;
- saved predictions alone can reproduce aggregate/fold metrics;
- all compared candidates share identical target rows;
- Manifest proves actual estimator params/features/train rows/code/config;
- deterministic FeedbackBuilder reports relative-to-baseline/parent diagnostics without using confirmation data;
- batch plan is frozen before batch execution.

## 4. V2-B adaptive/literature/queue gate

### Advisor
- live request includes task/protocol/capability/evaluation versions, remaining budget and current feedback;
- reviewed MethodCard evidence is optional but, when selected, appears as structured evidence with stable IDs;
- Round N+1 can cite real Round N artifacts;
- missing replay fixture fails; it never silently falls back to deterministic while claiming live;
- unsupported proposals are rejected by compiler.

### Literature
- paper fact, local observation and local inference are stored separately;
- proposal citations resolve to visible evidence;
- applicability mismatch is surfaced;
- selecting different reviewed evidence can change a reasonable proposal/explanation in controlled tests, but tests do not force arbitrary config changes;
- local negative evidence does not rewrite the paper claim.

### Execution/recovery
- idempotent submission;
- browser restart does not lose campaign state;
- completed candidates are not refit after recovery;
- failed/interrupted attempts are visible and consume budget;
- cancel semantics and late results are safe;
- concurrency limit is real, not only UI decoration.

### Product
- ResearchPackage export contains contract/evidence/hypotheses/attempts/predictions/results/limits;
- a real live-record campaign is replayable offline;
- “no improvement” remains a valid result.

## 5. V2.1 evidence/model-delivery gate

- focused results write to existing ExperimentMemory with task/data/protocol/eval/model-version compatibility keys;
- cold/warm Memory comparison uses the same task/budget and documents effects;
- engineering failure is not scientific negative evidence;
- Exposure Ledger binds data content/time ranges and access state;
- confirmation tool is unavailable to Advisor and only runs when eligible;
- refit policy is frozen before final training;
- ModelBundle loads in a fresh process and predicts on unlabeled latest-input schema;
- confirmation labels are never used to decide refit settings.

## 6. Shadow and future expansion

Shadow:
- prediction record is immutable and time-stamped;
- target later joins without rewriting the prior forecast;
- degradation triggers a research Mission, not automatic model replacement.

Demand-driven expansion:
- each new market/task has its own temporal/evaluation contract;
- broad literature retrieval is bounded, licensed, versioned and budgeted;
- new CodingAgent capability cannot modify evaluator, confirmation data, secrets or policy.

## 7. Required report for every submitted milestone

Record:
- base/head SHA;
- dependency/Python environment;
- exact test/lint/compile commands and exit codes;
- test scope and skipped external/native/live cases;
- input hashes and task versions for real-data acceptance;
- UI acceptance evidence when UI changed;
- documentation updated;
- rollback/compatibility note.

Do not claim that focused CI reran hour-scale historical native reproductions unless it actually did.
