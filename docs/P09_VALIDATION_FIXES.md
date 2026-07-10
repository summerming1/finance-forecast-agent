# P0.9 Validation Fixes

## Validation result

The validated P0.9 branch passed:

```text
31 pytest tests
Python compileall
11 MethodCards -> 11 PaperSpecs -> 22 candidate runs -> 22 success
approved-only integration: 1 approved card -> 1 report -> 1 golden card
```

## Fixed issues

1. Review state JSON is now loaded defensively and saved atomically.
2. Control Tower no longer counts pending cards as reviewed.
3. Reviews can affect execution through `--approved-only` and the corresponding UI checkbox.
4. Golden set materialization clears stale files and can require `approved` review status.
5. Adapter backlog regeneration preserves task status, assignee, and notes.
6. Adapter tasks can be edited in the Tasks & Timeline page.
7. Run Timeline IDs now use microseconds plus a UUID suffix, avoiding same-second collisions.
8. Run Timeline paths are project-relative and resolved through `project_dir`.
9. Timeline summaries distinguish available MethodCards from selected papers.
10. Timeline indexes are bounded to the latest 200 runs.

## Full local validation

PowerShell:

```powershell
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"

python -m pytest tests -q
python -m compileall -q src scripts apps tests

python scripts/run_methodcard_p0_pipeline.py `
  --cards-dir projects/finance_agent/method_cards_local_llm `
  --max-papers 11 `
  --max-candidates-per-paper 2 `
  --report-name methodcard_p0_report_p09_validated.json
```

## Approved-only validation

First approve one or more cards from MethodCard Review or Flow Trace. Then run:

```powershell
python scripts/run_methodcard_p0_pipeline.py `
  --cards-dir projects/finance_agent/method_cards_local_llm `
  --approved-only `
  --golden-approved-only `
  --max-papers 11 `
  --max-candidates-per-paper 2 `
  --report-name methodcard_p0_report_p09_approved.json
```

If no card is approved, the command stops with an explicit error instead of silently running all cards.

## Frontend

```powershell
python -m streamlit run apps/streamlit_app.py
```

Recommended sidebar values:

```text
Project directory: projects/finance_agent
MethodCards directory: projects/finance_agent/method_cards_local_llm
Report file: methodcard_p0_report_p09_validated.json
```

Suggested manual test order:

1. MethodCard Review: approve, reject, and mark needs revision; refresh and confirm persistence.
2. Workflow Runner: enable `Run approved MethodCards only` and run the workflow.
3. Flow Trace: confirm only approved papers appear in the approved-only report.
4. Tasks & Timeline: generate adapter backlog, edit task state, regenerate, and confirm the task state is preserved.
5. Materialize Golden sets with approved-only enabled and verify only approved cards are copied.
6. Run the workflow twice and verify two distinct Timeline entries are created.
