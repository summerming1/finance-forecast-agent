# Mission PR series — implementation and verification ledger

Original base: `571beb91ad8911cdb540192f6a0543755da6edb6`.

## PR-0: contract and gate

Approved ADR-MISSION-003; retained prior ADRs; established the Python 3.11/3.13 remote regression and offline source snapshot flow. No model algorithm changed. PR-0 gate: **21 passed; Ruff passed** on local Python 3.13. Local original gate: **19 passed**, Python 3.13, 2026-09-20.

Stages PR-1 through PR-6 remain unimplemented at this commit. Simulation and assistant-authored fixtures never count as real-user or live-provider acceptance. Historical native reproductions are not rerun by the focused gate.

## PR-1: evidence and truthful terminal states

Local Python 3.13: `python scripts/check_mission_gate.py --junit /mnt/data/pr1-junit.xml` — **33 passed; Ruff passed**. New negative/recompute coverage includes target/label alignment, duplicate rows, frozen plans before execution, all candidate failures, exposure identity/range, split bounds, evidence-tier escalation and label interval start. Existing 19 regressions remain active.

Separate real-data smoke: `PYTHONPATH=src python scripts/run_focused_spy_campaign.py --project-dir <output> --raw-spy-json <audited-spy-json> --source-metadata <audited-source-json> --max-fit-calls 40` — **4002 rows; 28 estimator fits + 8 statistic fits; completed_no_improvement; independent confirmation not run**. Reuses the audited Yahoo acquisition artifact, not a fresh network download. Synthetic tests are tagged in `tests/mission_support.py` and cannot satisfy scientific acceptance.

Changed evidence path, shared numeric evaluation, six baselines, manifests, feedback, append-time events and execution/outcome semantics. The exposure ledger is write-only governance at this milestone: its eligibility API fails closed until PR-5. Later stages remain pending. No historical native training or live LLM call was performed.
