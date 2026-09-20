# ADR-MISSION-PRODUCT-003: controlled product delivery and evidence gates

- Status: accepted
- Approved by: user, 2026-09-20, explicit request to implement PR-0 through PR-6 in order
- Supplements: ADR-FOCUS-001 and ADR-MISSION-002; does not rewrite historical scientific acceptance
- Base commit: `571beb91ad8911cdb540192f6a0543755da6edb6`
- Delivery branch: `feat/mission-product-pr0-pr6`

## Decision

Keep SPY / daily / next-session adjusted-close return / MAE / forecast-only. Preserve the existing Controller, LocalTaskQueue, ExperimentMemory, MethodAdapter and numerical evaluation authority. Mission is a thin entry point and Research Tree is a projection of recorded experiments, not another runtime.

Execute these gated increments, in order:

| Increment | Scope |
| --- | --- |
| PR-0 | Approved roadmap delta, reproducible baseline and acceptance contract |
| PR-1 | Row-level predictions, execution manifests, naive baselines, deterministic feedback, exposure records, truthful terminal states |
| PR-2 | Mission creation, workspace, actual configuration diffs and research history |
| PR-3 | Feedback/evidence-grounded decisions and fair Random/TPE/One-shot/Adaptive benchmark |
| PR-4 | Existing queue integration, idempotency, attempts, recovery, cancellation and complete ResearchPackage |
| PR-5 | Compatible Memory, confirmation eligibility/isolation and explicitly refitted ModelBundle |
| PR-6 | Same-task external CSV/Parquet and reviewed local Adapter pilot |

The previous increment's relevant regression tests must pass before starting the next. Tests remain cumulative. A focused green gate never implies historical native training, live-provider quality, commercial demand or financial performance has been validated.

## Roadmap delta

V2-A = PR-1 + PR-2. V2-B = PR-3 + PR-4. V2.1 = PR-5. V2.2 engineering pilot = PR-6. Controlled BYO precedes the complete V3 Shadow Forecasting product. Real user research may start immediately; it is not claimed by synthetic tests. Lightweight forward records may start only when the inference/time contract is reliable. Historical backfills never count as forward predictions.

## Evidence and testing

Use four independent gates: engineering, research-process/scientific evidence, product usability, and agent/commercial value. Failure to improve is valid only after usable research evidence exists; execution failure/cancellation must not become a scientific negative result.

The user authorizes synthetic external datasets/models and assistant-authored LLM fixtures to test functionality. Label them `simulation_only` / `assistant_authored_fixture`. Never report those as customer trials, live API calls, independent confirmation, real market performance or demonstrated agent value. Preserve a runnable live-record/replay interface, but disclose when no live provider was called.

Start exposure recording in V2-A, including content/time identity, access purpose and provenance. Existing SPY history is exposed; external unknown provenance is not independent confirmation. Memory is a compatibility-filtered weak prior, never numerical authority; tenant data is not mixed.

## Safety and non-goals

No arbitrary uploaded Python/notebooks/pickle execution, automatic trading, new assets/tasks, unconstrained literature crawling, evaluator edits by the Advisor, new agent framework, graph database, Kubernetes or duplicate core services. External code runs only through a reviewed local registration with explicit capability and artifact contracts. Local review is not an OS sandbox or a security certification.

## Acceptance accounting

Record exact code revision, commands, exit codes, environment, test layers, real versus simulated inputs, skipped cases and remaining limitations in the release note. Functional implementation does not close live-LLM, true held-out or paying-user gates. Keep CURRENT_IMPLEMENTATION factual and the roadmap aspirational where work is still open.
