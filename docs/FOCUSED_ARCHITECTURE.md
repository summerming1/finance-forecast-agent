# Focused / Mission Research Architecture

> Status: APPROVED. ADR-FOCUS-001 establishes the SPY focused line; ADR-MISSION-002 consolidates the Mission architecture/literature role; ADR-MISSION-PRODUCT-003 adds gated PR delivery, Agent value validation and controlled BYO-before-Shadow ordering. Actual implementation status is always defined by CURRENT_IMPLEMENTATION.md.

## 0. Approved gated delivery sequence

```text
PR-1 / V2-A  Evidence Foundation
PR-2 / V2-A  Mission + Research Workspace
PR-3 / V2-B  Adaptive Research + Agent Value Benchmark
PR-4 / V2-B  Persistent Execution + ResearchPackage
PR-5 / V2.1  Memory + Confirmation + ModelBundle
PR-6 / V2.2  Controlled BYO Data/Model Pilot
V3           Shadow Forecasting
```

Research Tree is a read-only/product projection of recorded parent/hypothesis/experiment/config-diff/result facts, not a second graph execution engine. Exposure recording starts in V2-A; confirmation isolation remains V2.1. Execution status and research outcome are separate dimensions so engineering failure cannot become a scientific negative result.

## 1. Product definition

The product is a **financial machine-learning research workbench**: given an approved task, data snapshot, starting models, evidence and budget, it repeatedly proposes falsifiable hypotheses, executes controlled experiments, evaluates them deterministically, and decides whether to continue, diagnose, simplify or stop.

The current supported product task remains:
- SPY;
- daily;
- next observed XNYS trading-session adjusted-close return;
- regression;
- MAE primary metric;
- forecast-only;
- historical-development exposure.

A correct “no improvement” outcome is a successful research process.

## 2. User-facing flow

```text
Mission
  “Improve SPY next-session return prediction”
        |
        v
TaskSpec + data snapshot + starting model/baselines
        |
        v
Campaign preflight
  data / time / evaluation / capabilities / budget / exposure
        |
        v
Research rounds
  evidence -> hypothesis -> experiment plan -> execution -> feedback
        |
        +----> next batch / diagnose / falsify / simplify / stop
        |
        v
ResearchPackage
        |
        +----> optional approved refit -> ModelBundle
        |
        +----> future shadow forecasting
```

The old seven-stage literature/native-reproduction workbench remains an advanced/professional path.

## 3. Object boundaries

| Object | Owns | Must not duplicate |
|---|---|---|
| Mission | user question, mission type, links to tasks/campaigns | label/data/budget/runtime state |
| TaskSpec | entity, frequency, horizon, label, information timing, primary metric | campaign budget/results |
| CampaignSpec | frozen dataset/protocol/capability scope/budget/approval | long-term user goal |
| HypothesisSpec | mechanism, evidence refs, expected observation, falsification condition | metric computation |
| Candidate/ExperimentPlan | actual model, params, features, window, seed | research narrative authority |
| Attempt/Run | execution status, resource use, retries, artifacts | scientific verdict |
| PredictionArtifact | target rows, y_true/y_pred, fold/time metadata | prose interpretation |
| Feedback | deterministic diagnostics and evidence boundaries | hidden/final labels exposed to Advisor |
| ResearchPackage | complete research history and reproducibility information | unverified production claim |
| ModelBundle | explicit approved refit output and inference contract | last fold model disguised as final |

Mission is intentionally thin.

## 4. Single-controller architecture

```text
Streamlit / CLI
      |
      v
MissionService (thin product entry)
      |
      v
TaskSpec + CampaignSpec
      |
      v
ResearchController  <-- only research authority
      |
      +-- ContextBuilder
      |     task/protocol/capabilities
      |     development feedback
      |     reviewed MethodCard evidence
      |     compatible Memory (later)
      |
      +-- ResearchAdvisor
      |     deterministic baseline policy
      |     live-record
      |     strict replay
      |
      +-- PlanCompiler
      |     model/feature/param/evidence/approval/budget gates
      |
      +-- LocalTaskQueue -> worker
      |
      +-- ExecutionManifest + PredictionArtifact
      |
      +-- DevelopmentEvaluator + FeedbackBuilder
      |
      +---------------> next round or stop

Independent confirmation:
 frozen candidate + exposure/access gate -> ConfirmationWorker
```

These are logical responsibilities, not microservices.

## 5. Literature as continuous research evidence

Literature is optional for starting a task but must be first-class evidence when selected.

### What stays in MethodCard / Evidence
- what question the paper studies;
- mechanism/hypothesis actually stated;
- data and applicability conditions;
- method and training/evaluation details;
- reported results;
- limitations/null results/counter-evidence where available;
- exact evidence location.

### What stays in local HypothesisSpec
- why that paper evidence may matter to this task;
- current local diagnostic evidence;
- proposed local change;
- expected observation;
- falsification condition;
- known transfer gap.

Never write local conclusions back as paper facts.

### V2 literature behavior
V2 uses a small reviewed local literature set. ContextBuilder supplies only relevant evidence snippets/structured claims, not every full PDF each round.

A formal proposal must distinguish evidence source types:
- `paper_claim`
- `current_experiment`
- `compatible_memory`
- `domain_hypothesis`

The compiler verifies that cited evidence exists and is visible to the campaign. A citation is traceability, not proof of the local hypothesis.

### Later literature behavior
Only after the reviewed-evidence loop is useful:
```text
research knowledge gap
 -> bounded search query
 -> metadata/full-text acquisition under license
 -> MethodCard/evidence extraction
 -> applicability review
 -> optional human approval
 -> next research batch
```
Search/read cost is budgeted and versioned. No uncontrolled “search the web every round”.

## 6. Research actions

Advisor actions are not just “pick a model”:
- diagnose;
- improve;
- falsify/control/ablate;
- simplify/converge;
- stop/request evidence.

One hypothesis may require multiple experiments. If only one component is claimed causal, other relevant components stay fixed.

Joint changes are allowed for exploration but the conclusion must say “joint change”, not falsely attribute the gain to one feature.

## 7. Deterministic numeric authority

LLMs may propose mechanisms and experiments. They do not own:
- target construction;
- split construction;
- feature availability;
- metrics;
- resource gates;
- implementation conformance;
- confirmation access;
- strict-reproduction acceptance;
- model promotion.

FeedbackBuilder produces authoritative numerical diagnostics. An optional future Critic can explain these diagnostics but cannot change them.

## 8. Data/time contract

The focused task uses adjusted-close returns. Missing adjusted-close data is an error, not a close-price fallback.

Minimum time concepts:
- session_date;
- available_at precision/assumption;
- decision_time;
- label interval;
- target_observed_at.

The current historical Yahoo data is vendor-adjusted and not claimed to be institutionally point-in-time. XNYS session completeness is validated for the focused dataset; future other markets need their own calendar contract.

All candidate comparisons use the same evaluation target rows. Split requirements and dataset minimum size come from the same split policy.

## 9. Budget/evaluation separation

`ResearchBudget` owns resources: rounds, candidate count, fit calls, wall time/LLM cost as implemented.

`EvaluationPolicy` owns research screening: primary metric and development threshold.

Budget is checked and reserved before work. Failed attempts consume resources. Development screening is not independent confirmation.

## 10. State and persistence roadmap

V1.1 keeps the current synchronous campaign but fixes preflight and result semantics.

V2-B moves to existing LocalTaskQueue semantics with persistent attempts/events/idempotency and candidate-boundary recovery. Do not create `task_queue_v2`.

Events are facts recorded when they happen, not reconstructed afterward.

## 11. Deliverables

### ResearchPackage
Always possible when a campaign completes or stops: task/contract, evidence, hypotheses, experiments, failures/retries, predictions, metrics, environment/lineage and reproduction instructions.

### ModelBundle
Only after explicit selection/refit policy and actual refit. Includes model, preprocessing, FeatureSpec, task, cutoff, dependencies, lineage and inference entry point. A validation-fold estimator is not automatically a ModelBundle.

## 12. External-framework lessons

RD-Agent: separate research proposal, implementation/execution and feedback; results must influence the next research decision.

DeepSeek Harness: stable tool interfaces, provider/consumer separation, approval/policy gates and observable execution.

We borrow principles, not whole runtimes. This repository remains the authority on financial time semantics, reproducibility and evidence quality.
