# ADR 007 V2.5.0 bounded feature and training-window research

- status: accepted
- approved_by: user
- approved_at: 2026-10-19
- authoritative_branch: feat/mission-research-v2
- review_base: c6bdd282dd97952cab37cc64e8edb7f4549cb70f
- implementation_authorized: N0–N5, local scoped commits, isolated synthetic engineering

The user explicitly approved replacing the conditional window-only next step with
one Campaign that can choose features or training_window, with one declared axis
per experiment relative to an accepted control. The sole execution contract is
[V2_5_METHOD_RESEARCH.md](V2_5_METHOD_RESEARCH.md). Approval is not acceptance.

Reuse Controller/Queue/RuntimeDB/Evaluator/Memory/Evidence and the workspace.
Ridge/StandardScaler parameters, seed, builtin groups and uniform weights stay
fixed. Existing price ASTs plus expanding/rolling504/756, two plans/four slots,
MAE/0.0025. Complete methods survive cache, recovery, continuation and explicit
window-consistent refit. Semantic updates share the original Advisor response;
they cannot override numeric facts or selection. Three training scopes remain
distinct; history needed by causal features is not cut at the training window.

Costs include versioned candidates/responses, actual training receipts, separate
diagnostic calibration, trusted delivery and end-to-end regression. Old schemas,
fixtures, hashes and exposure remain unchanged. Existing active contracts need
their original source/environment, not a hash rewrite or an empty replacement DB.

No real Provider, fees, material sends, real-market research, sealed labels,
production migration, global permission changes, remote CI or push. Synthetic
worker/fit/predict/refit/local HTTP/replay/browser and local commits are authorized.
G6 remains attempted with issues pending human recheck. P/F/M, weights, HPO,
knowledge, internal coding, Shadow and publishing remain conditional future work.

Implementation evidence recorded 2026-10-19: N0–N5 bounded synthetic engineering, 59 new tests and four browser modes pass; full regression retains two historical failures. Exact status belongs only to CURRENT_IMPLEMENTATION.md and evidence to V2_5_METHOD_RESEARCH.md §9. This note does not change this ADR approval, authorize future packages, or sign financial/Provider/human acceptance.
