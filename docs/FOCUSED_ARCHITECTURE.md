# Focused / Mission Research Architecture

## V2.5.0 extension (2026-10-19; bounded engineering verified)

ADR007 and V2_5_METHOD_RESEARCH.md authorize one feature_window profile in the existing Controller. Full methods inherit from accepted controls; one axis changes per experiment. Three scopes separate comparison/calibration, eligible and selected training. Same-response research_update remains advice, never numeric authority. Actual fit receipts and versioned window-consistent refit reuse existing runtime/trust. Old contracts are historical and remain compatible; no second service or state store.


Final evidence is in V2_5_METHOD_RESEARCH.md §9 and CURRENT_IMPLEMENTATION.md. Compact method references are reversible planning projections, not stored semantic or numeric authority; actual candidates/bundles keep full legal methods. Old source-bound campaigns are not silently migrated.

Reading rule (2026-10-20): the V2.5 extension above is current; dated sections below record earlier increments and reusable responsibilities. Their then-future window-only scope does not constrain the approved two-axis profile. No new architectural authority or platform is introduced by the documentation sync.

## S0–S4 bounded extension (2026-10-13)

The existing immutable observation objects carry finite prediction/comparison identity, first-event provenance and evidence tier. The comparison index is a read-only reconstruction, not a new store. New diagnostic v3 contracts freeze four-part research decisions and R/D/J support; legacy reference designs remain explicit, not fabricated judgment. Numerical observations, primary selection and conservative final recommendation remain separate. ON planning receives bounded visible comparison summaries; OFF receives neither these nor the new diagnostic package. Full audit objects do not become a second planning truth. Existing UI/package projections read those same objects; original explicit refit and external trusted registry remain the only model-delivery chain. Formal roadmap and future execution capabilities are unchanged.

> Status: APPROVED. ADR-FOCUS-001 establishes the SPY focused line; ADR-MISSION-002 consolidates the Mission architecture/literature role; ADR-MISSION-PRODUCT-003 adds gated PR delivery, Agent value validation and controlled BYO-before-Shadow ordering. Actual implementation status is always defined by CURRENT_IMPLEMENTATION.md.

## Historical V2.4 diagnostic extension

The 2026-10-10 repair uses explicit v2 planning projection: identical facts are interned in a deterministic small-reference table bound by the original frozen prompt hash; columnar loss records retain complete group/fold numeric entries. The full audit keeps original scope hashes, raw provenance and named feature statistics. This is a pure projection inside the existing Controller, not a new context engine or state authority. Cached controlled observations are keyed by proposal and project all completed events; OFF excludes the entire new source table. The fixed diagnostic comparator is bound before the first decision; numeric selection authority is unchanged. Test-start/end manifests are audit exports, not a replacement for RuntimeDB or historical receipts.

[ADR006](ADR_MISSION_PRODUCT_006.md) and [V2_4_DIAGNOSTIC_RESEARCH.md](V2_4_DIAGNOSTIC_RESEARCH.md) define the approved diagnostic/observation increment. Actual implementation and evidence are in CURRENT_IMPLEMENTATION.md. The original Controller invokes pure projections and persists frozen evidence in the existing RuntimeDB; OFF/ON differ in visible information, not compiler permissions. ModelBundle remains an explicitly refitted trusted model, not diagnostic JSON. Future windows, weights, ensembles and Shadow are conditional roadmap items, not this increment.

## Historical approved V2.3 extension (approval was not a completion claim)

[ADR005](ADR_MISSION_PRODUCT_005.md) is accepted; [the consolidated V2.3 specification](V2_3_FEATURE_RESEARCH.md) owns the detailed contract. Existing authorities below are retained; actual delivered behavior remains in CURRENT_IMPLEMENTATION.md.

The proposal adds a data-only FeatureProgram and pure raw-price feature computation inside the existing compile/evaluate path. Candidate/program identity must survive Mission submission, persistent request, CLI worker, frozen plan, recovery, continuation, refit and raw unlabeled inference. Legacy objects retain their identities. DSL confirmation rejection must be introduced with schema dispatch, before executable integration; a valid caller-computed hash does not authorize a capability.

RuntimeDB remains runtime authority, and existing Memory/MethodCard remain their respective semantic/source authorities. No additional engine, state database, numerical evaluator or permissions platform is proposed. Common research warm-up and actual bundle lookback are separate. Training-time partial completion cannot be rolled back as a free failed batch. These are planned requirements, not claims about current interfaces.

## 0. Approved gated delivery sequence

```text
PR-1 / V2-A  Evidence Foundation
PR-2 / V2-A  Mission + Research Workspace
PR-3 / V2-B  Adaptive Research + Agent Value Benchmark
PR-4 / V2-B  Persistent Execution + ResearchPackage
PR-5 / V2.1  Memory + Confirmation + ModelBundle
PR-6 / V2.2  Controlled BYO Data/Model Pilot
V2.3         Controlled price feature research
V2.4         Deterministic diagnostic / observation research
V3           Shadow Forecasting (separately approved, conditional)
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
      |     compatible Memory (implemented; cold in the V2.4 pilot)
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

## V2.2-R transactional storage refinement

R2 retains LocalTaskQueue and FocusedResearchController as the only scheduling and research authorities. RuntimeDB is an embedded SQLite persistence primitive, not another runtime. CampaignRuntime owns only durable contracts, leases, attempts, frozen plans and accepted artifact references; it does not choose research actions or evaluate models. JSON/JSONL are exports. Queue-submitted campaigns share the queue's database so cancellation and generation checks participate in the same transaction boundary.

An accepted artifact is immutable and hash-bound to its execution contract. A file written before acceptance is an orphan audit artifact, not a reusable completed experiment. Interrupted reservations remain charged; retries receive new attempt identities. No exactly-once physical computation guarantee is made. Multi-host scheduling, OS security isolation and automatic migration of unverifiable legacy attempts remain out of scope.


## R6 integration within existing authorities

`research_mission.py` contains thin product composition functions; it does not own a second execution state. Project/Mission links, held submissions and immutable input requests share RuntimeDB with LocalTaskQueue and the existing Controller. The Streamlit view renders canonical accepted result projections regardless of submission-button state. Query navigation contains only validated IDs; filesystem/tenant authority is operator configuration.

ReviewedNumericFeature extends the existing feature registry per execution, never the process-global registry. Controller → compiler → evaluator → Manifest → refit consume the same frozen registry; Memory compatibility includes feature-spec identity. BYO time checks use sessions plus separate timezone-aware actual instants and report declared versus verified provenance.

ResearchPackage is an export, not runtime authority. ModelBundle uses R4 external registration; download alone does not authorize deserialization elsewhere. UI-triggered explicit refit is a single controlled delivery operation, not automatic promotion/ongoing model deployment. Shared worker semantics and research budget remain independent of browser redraws.


## Approved B0–B5 supplement (not a completion claim)

Two entry modes map to the same Campaign; incumbent, fixed controls and candidates have separate roles, with compatible execution reuse. RuntimeDB remains the only execution state; decision→logical call→HTTP attempts retain unknown costs and bounded provider waits.

Literature: existing source / MethodCard revision → purpose-specific approval → permission-filtered EvidenceIndex → transfer hypothesis with use_role/transfer_gap → frozen action/actual config diff → deterministic local feedback → next decision. No separate literature database or controller. Review-for-research may accept theory/limitations without empirical metrics; strict reproduction gates remain unchanged. Source version changes require an explicit new Campaign; permission revocation prevents subsequent external sends.

Batch planning is opt-in and frozen before fits. Compact context preserves all experiment statuses and key negatives. Common experiment contracts and strategy-specific settings are distinct; G2A strategies and G2B explicit-literature treatment are separate comparisons. Report traceability, semantic review and incremental value separately.

## B2 implementation detail

`entry_mode` changes initialization only. Fixed controls retain their versioned recipes. A user incumbent is separately evaluated or aliases a control with identical execution fingerprint; `candidate_roles` is a projection, not a second evaluator. `features_only` is compiled and revalidated at execution. A persistent refit record binds project/campaign/candidate/refit IDs to the externally trusted ModelBundle. Downloads use the same byte verifier as deserialization without loading pickle.

## B3 literature-grounded projection

Existing source bytes → immutable MethodCardV3 revision → purpose-specific review in existing approval document → tenant/provider-filtered EvidenceIndex → local transfer hypothesis → actual candidate + diff + feedback. One truth source, no crawler/vector service. Integrity hashes do not certify scientific correctness or semantic entailment. The operator reviews source fidelity; required capabilities are not substituted. Revocation blocks new sends; a frozen source update is not silently adopted.

The native Advisor stays shared. `adaptive_batch` freezes at most the configured batch size before fit; old adaptive and one-shot remain separate. Catalog IDs deterministically resolve before existing action compiler. Compact context uses a versioned deterministic projection retaining experiment states and limitations. G2A keeps data/evaluation/budgets/common context separate from strategy provider policy; G2B varies only explicit literature with one fixed strategy and cold/frozen Memory. All external-quality claims remain pending actual provider/user evidence.

## B4 read-only summary and explicit continuation
`focused_summary.build_research_summary` is a pure projection, not an evaluator or truth store. `workspace_research_summary` binds ancestor costs to accepted parents. `continuation_from` carries parent project/campaign/candidate/config/result/final/contract identities and seed; it is revalidated in submission and actual Controller initialization. No prediction reuse is implied. The same Mission and state authority retain historical exposures and refits. New data and new replay plans are explicit separate workflows, not silently compatible resumes.

Capability-only confirmation preflight precedes registry access; its not_checked data eligibility cannot authorize execution. Existing fixed-holdout evaluator and train-only naive evaluator handle controlled baselines. Statistic computations are distinct from estimator fits; grant consumption remains one-shot. Summary exports obey the existing restricted-literature projection.

### B5 validation-only boundary
The frozen-SPY auditor reads existing predictions and delegates refit/load/package to existing APIs; it owns no campaign or metric authority. The original raw hash is pinned. Independent arithmetic detects corruption; it cannot promote development evidence. Core CI and browser evidence are separate from unavailable external inputs, real provider reliability, literature semantics and true user outcomes.

## V2.4 diagnostic extension (ADR006)

Pure focused_diagnostics functions derive diagnostics only from accepted PredictionArtifact, contract-bound raw history and actual training masks. The original Controller owns invocation, frozen context/design/observation/recommendation; RuntimeDB persists them with existing immutable artifact references. No second evaluator, queue or Memory. Automatic derivation does not fit; missing train predictions remain unavailable. OFF planning projection excludes new diagnostics/observations, and the initial pilot uses cold Memory to exclude indirect retrieval leakage. Memory itself is already implemented.

## 2026-10-14 当前V2.4增量索引

唯一详细合同和N01—N22映射见`V2_4_DIAGNOSTIC_RESEARCH.md`当日增量。新v4 J门禁与实际schema一致；R/D/Random保持参考合同。原Controller从冻结上下文/计划推导观察形成时点，不从缓存命中推导；原RuntimeDB仍是权威，不重分类旧事件。第二轮仅有界关联原判断与获准结果，OFF不读取新增观察；共享字段压缩不截断数值，原64k和2规划/4槽不变。真实两入口技术driver复用WorkspaceUI/Queue/evaluator/trust，隔离测试库不是新增状态系统。
