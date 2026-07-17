from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from finance_forecast_agent.native_execution import (
    MetricTarget,
    NativeClaimSpec,
    OfficialRepoCommandAdapter,
    _format_command,
    _spec_sha256,
    audit_native_claim,
    discover_native_reports,
    load_native_claim_catalog,
    reconcile_native_report_artifacts,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _governance(tmp_path: Path) -> tuple[Path, Path]:
    card = tmp_path / "card.json"
    plan = tmp_path / "plan.json"
    card.write_text(
        json.dumps(
            {
                "approval_required": False,
                "extraction_metadata": {
                    "evidence_verification": {"passed": True, "span_count": 2, "errors": []}
                },
            }
        ),
        encoding="utf-8",
    )
    plan.write_text(
        json.dumps(
            {
                "plan_mode": "native_reproduction",
                "strict_ready": True,
                "approved_for_execution": True,
            }
        ),
        encoding="utf-8",
    )
    return card, plan


def _spec(tmp_path: Path, *, expected: float = 0.1, repetitions: int = 2) -> NativeClaimSpec:
    dataset = tmp_path / "data.csv"
    archive = tmp_path / "source.zip"
    source = tmp_path / "source"
    source.mkdir()
    entrypoint = source / "runner.py"
    dataset.write_text("x\n1\n", encoding="utf-8")
    archive.write_bytes(b"official-source")
    entrypoint.write_text("print('fixture')\n", encoding="utf-8")
    card, plan = _governance(tmp_path)
    return NativeClaimSpec(
        paper_id="paper",
        claim_id="paper_claim",
        title="Paper",
        paper_url="https://example.test/paper",
        claim_locator="Table 1",
        model_name="Fixture",
        experiment_type="forecast_only",
        dataset_id="fixture",
        dataset_path=str(dataset),
        dataset_sha256=_hash(dataset),
        source_repository="owner/repo",
        source_revision="abc123",
        source_archive_path=str(archive),
        source_archive_sha256=_hash(archive),
        source_root=str(source),
        source_entrypoint="runner.py",
        source_entrypoint_sha256=_hash(entrypoint),
        source_license="MIT",
        command=[sys.executable, "-c", "print('mse:0.101, mae:0.202')"],
        metrics={
            "mse": MetricTarget(expected=expected, absolute_tolerance=0.01),
            "mae": MetricTarget(expected=0.2, absolute_tolerance=0.01),
        },
        metric_patterns={
            "mse": r"mse:([0-9.]+)",
            "mae": r"mae:([0-9.]+)",
        },
        protocol={"split": "chronological"},
        repetitions=repetitions,
        method_card_path=str(card),
        reproduction_plan_path=str(plan),
    )


def test_official_repo_adapter_runs_repetitions_and_checks_predeclared_metrics(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    report = OfficialRepoCommandAdapter().run(
        tmp_path,
        spec,
        output_path=tmp_path / "reports" / "native_fixture.json",
    )
    assert report["complete_reproduction_allowed"] is True
    assert report["required_repetitions"] == 2
    assert len(report["runs"]) == 2
    assert report["metrics"] == pytest.approx({"mse": 0.101, "mae": 0.202})
    assert report["metric_checks"]["mse"]["passed"] is True
    assert discover_native_reports(tmp_path)[0]["claim_id"] == "paper_claim"


def test_official_repo_adapter_binds_predeclared_parameters_per_run(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    payload = spec.to_dict()
    payload["command"] = [
        "{python}",
        "-c",
        "print('seed={seed}, mse:0.101, mae:0.202')",
    ]
    payload["run_parameters"] = [{"seed": "2021"}, {"seed": "2022"}]

    report = OfficialRepoCommandAdapter().run(tmp_path, NativeClaimSpec.from_dict(payload))

    assert [run["run_parameters"]["seed"] for run in report["runs"]] == ["2021", "2022"]
    assert "seed=2021" in report["runs"][0]["stdout_tail"]
    assert "seed=2022" in report["runs"][1]["stdout_tail"]


def test_command_formatter_resolves_conda_executable(tmp_path: Path, monkeypatch) -> None:
    conda = tmp_path / "conda.exe"
    monkeypatch.setenv("CONDA_EXE", str(conda))

    command = _format_command(
        ["{conda}", "run", "-n", "paper-env", "python", "{source_root}/run.py"],
        project_dir=tmp_path,
        source_root=tmp_path / "source",
        dataset_path=tmp_path / "data.csv",
        runtime_root=tmp_path / "runtime",
        run_index=0,
    )

    assert command[0] == str(conda)
    assert Path(command[-1]) == tmp_path / "source" / "run.py"


def test_official_repo_adapter_isolates_repeated_attempt_checkpoints(tmp_path: Path) -> None:
    spec = _spec(tmp_path, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; "
            "p=Path(r'{runtime_root}')/'marker'; "
            "print(f'mse:{{0.101 if not p.exists() else 9.0}}, mae:0.202'); "
            "p.write_text('attempt')"
        ),
    ]
    isolated_spec = NativeClaimSpec.from_dict(payload)
    adapter = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime")

    first = adapter.run(tmp_path, isolated_spec)
    second = adapter.run(tmp_path, isolated_spec)

    assert first["complete_reproduction_allowed"] is True
    assert second["complete_reproduction_allowed"] is True
    assert first["runtime_execution_root"] != second["runtime_execution_root"]
    assert Path(first["runtime_execution_root"]).parent == tmp_path / "runtime" / "r"
    assert len(Path(first["runtime_execution_root"]).name) == 12
    assert first["runs"][0]["working_directory"] != second["runs"][0]["working_directory"]


def test_official_repo_adapter_persists_timeout_as_a_failed_report(tmp_path: Path) -> None:
    spec = _spec(tmp_path, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = ["{python}", "-c", "import time; time.sleep(1)"]
    payload["timeout_seconds"] = 0.01
    output = tmp_path / "reports" / "native_timeout.json"

    report = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime").run(
        tmp_path,
        NativeClaimSpec.from_dict(payload),
        output_path=output,
    )

    assert report["complete_reproduction_allowed"] is False
    assert report["execution_passed"] is False
    assert report["runs"][0]["timed_out"] is True
    assert report["runs"][0]["exit_code"] == 124
    assert any("predeclared timeout" in blocker for blocker in report["blockers"])
    assert json.loads(output.read_text(encoding="utf-8"))["runs"][0]["timed_out"] is True


def test_official_repo_adapter_resumes_completed_repetitions(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    payload = spec.to_dict()
    counter = tmp_path / "counter.txt"
    payload["command"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; "
            f"p=Path(r'{counter}'); "
            "n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); "
            "print('mse:0.101, mae:0.202')"
        ),
    ]
    resumable = NativeClaimSpec.from_dict(payload)
    output = tmp_path / "reports" / "native_resume.json"
    adapter = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime")

    partial = output.with_suffix(output.suffix + ".partial")
    partial.parent.mkdir(parents=True)
    execution_root = tmp_path / "runtime" / "r" / "resume-test"
    first_run = {
        "run_index": 0,
        "run_parameters": {},
        "command": ["seeded-completed-run"],
        "working_directory": str(execution_root / "work"),
        "exit_code": 0,
        "timed_out": False,
        "duration_seconds": 1.0,
        "metrics": {"mse": 0.101, "mae": 0.202},
        "metric_values": {"mse": [0.101], "mae": [0.202]},
        "metric_artifacts": [],
        "stdout_tail": "mse:0.101, mae:0.202",
        "stderr_tail": "",
    }
    partial.write_text(
        json.dumps(
            {
                "schema_version": "native_partial_report_v1",
                "claim_id": resumable.claim_id,
                "spec_sha256": _spec_sha256(resumable),
                "runtime_execution_root": str(execution_root),
                "working_directory": str(execution_root / "work"),
                "runs": [first_run],
                "elapsed_seconds": 1.0,
            }
        ),
        encoding="utf-8",
    )

    report = adapter.run(tmp_path, resumable, output_path=output)

    assert report["complete_reproduction_allowed"] is True
    assert len(report["runs"]) == 2
    assert report["resumed_from_partial"] is True
    assert counter.read_text() == "1"
    assert not partial.exists()


def test_official_repo_adapter_formats_runtime_environment_and_seeds_empty_partial(
    tmp_path: Path,
) -> None:
    spec = _spec(tmp_path, repetitions=1)
    payload = spec.to_dict()
    payload["environment"] = {"FIXTURE_STATE": "{runtime_root}/state.bin"}
    payload["command"] = [
        "{python}",
        "-c",
        "import os; print('mse:0.101, mae:0.202, state=' + os.environ['FIXTURE_STATE'])",
    ]
    output = tmp_path / "reports" / "native_environment.json"

    report = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime").run(
        tmp_path,
        NativeClaimSpec.from_dict(payload),
        output_path=output,
    )

    expected_state = str(Path(report["runtime_execution_root"]) / "state.bin")
    actual_state = report["runs"][0]["stdout_tail"].split("state=", 1)[1].strip()
    assert Path(actual_state) == Path(expected_state)
    assert report["complete_reproduction_allowed"] is True


def test_official_repo_adapter_rejects_incomplete_run_parameter_matrix(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    payload = spec.to_dict()
    payload["run_parameters"] = [{"seed": "2021"}]

    with pytest.raises(ValueError, match="run_parameters"):
        OfficialRepoCommandAdapter().run(tmp_path, NativeClaimSpec.from_dict(payload))


def test_native_audit_blocks_hash_drift_and_unresolved_assumptions(tmp_path: Path) -> None:
    spec = _spec(tmp_path)
    Path(spec.dataset_path).write_text("changed", encoding="utf-8")
    payload = spec.to_dict()
    payload["unresolved_assumptions"] = ["unknown split"]
    audit = audit_native_claim(tmp_path, NativeClaimSpec.from_dict(payload))
    assert audit["passed"] is False
    assert any("dataset SHA256" in blocker for blocker in audit["blockers"])
    assert any("unknown split" in blocker for blocker in audit["blockers"])


def test_native_catalog_rejects_duplicate_claim_ids(tmp_path: Path) -> None:
    spec = _spec(tmp_path).to_dict()
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({"claims": [spec, spec]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_native_claim_catalog(catalog)


def test_semantic_noop_patch_uses_a_runtime_copy(tmp_path: Path) -> None:
    spec = _spec(tmp_path, repetitions=1)
    entrypoint = Path(spec.source_root) / spec.source_entrypoint
    original = entrypoint.read_text(encoding="utf-8")
    payload = spec.to_dict()
    payload["command"] = ["{python}", "{source_root}/runner.py"]
    payload["metric_patterns"] = {}
    payload["metrics"] = {}
    payload["compatibility_patches"] = [
        {
            "path": "runner.py",
            "classification": "semantic_noop",
            "old": "print('fixture')",
            "new": "print(\"fixture\")",
            "rationale": "Equivalent quoting for compatibility coverage.",
        }
    ]
    patched = NativeClaimSpec.from_dict(payload)
    audit = audit_native_claim(tmp_path, patched)
    assert audit["passed"] is False
    assert "paper claim has no metric targets" in audit["blockers"]

    payload["metrics"] = {"fixture": {"expected": 1.0, "absolute_tolerance": 0.0}}
    payload["metric_patterns"] = {"fixture": r"(fixture)"}
    # Exercise preparation through a numeric command while retaining a patched source copy.
    payload["command"] = ["{python}", "-c", "print('fixture=1.0')"]
    payload["metric_patterns"] = {"fixture": r"fixture=([0-9.]+)"}
    report = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime").run(
        tmp_path, NativeClaimSpec.from_dict(payload)
    )
    assert report["complete_reproduction_allowed"] is True
    assert report["source"]["compatibility_patches"][0]["classification"] == "semantic_noop"
    assert entrypoint.read_text(encoding="utf-8") == original


def test_adapter_aggregates_multiple_metric_observations_from_one_process(tmp_path: Path) -> None:
    spec = _spec(tmp_path, expected=0.15, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = [
        "{python}",
        "-c",
        "print('mse:0.1, mae:0.2\\nmse:0.2, mae:0.2')",
    ]
    payload["expected_metric_observations"] = 2
    report = OfficialRepoCommandAdapter().run(tmp_path, NativeClaimSpec.from_dict(payload))

    assert report["complete_reproduction_allowed"] is True
    assert report["metric_aggregate"]["mse"]["values"] == [0.1, 0.2]
    assert report["metrics"]["mae"] == pytest.approx(0.2)


def test_artifact_metrics_override_validation_log_observations(tmp_path: Path) -> None:
    spec = _spec(tmp_path, expected=0.1, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = [
        "{python}",
        "-c",
        (
            "from pathlib import Path; import numpy as np; "
            "p=Path('results/native_0'); p.mkdir(parents=True); "
            "np.save(p/'test_metrics.npy', np.array([0.2, 0.1])); "
            "print('mse:9, mae:9')"
        ),
    ]
    payload["expected_metric_observations"] = 1
    payload["metric_artifact_glob"] = "results/*/test_metrics.npy"
    payload["metric_artifact_indices"] = {"mae": 0, "mse": 1}
    report = OfficialRepoCommandAdapter(runtime_root=tmp_path / "runtime").run(
        tmp_path, NativeClaimSpec.from_dict(payload)
    )

    assert report["complete_reproduction_allowed"] is True
    assert report["metrics"] == pytest.approx({"mse": 0.1, "mae": 0.2})
    assert report["metric_source"] == "official_test_artifacts"
    assert report["runs"][0]["metric_artifacts"][0]["metrics"]["mse"] == 0.1

    report["runs"][0]["metric_values"] = {"mse": [9.0], "mae": [9.0]}
    reconciled = reconcile_native_report_artifacts(report, NativeClaimSpec.from_dict(payload))
    assert reconciled["complete_reproduction_allowed"] is True
    assert reconciled["metric_source"] == "official_test_artifacts"


def test_last_observation_policy_ignores_intermediate_evaluations(tmp_path: Path) -> None:
    spec = _spec(tmp_path, expected=0.2, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = ["{python}", "-c", "print('mse:9, mae:9\\nmse:0.2, mae:0.2')"]
    payload["metric_observation_policy"] = "last"
    report = OfficialRepoCommandAdapter().run(tmp_path, NativeClaimSpec.from_dict(payload))

    assert report["complete_reproduction_allowed"] is True
    assert report["metric_aggregate"]["mse"]["values"] == [0.2]


def test_observation_count_mismatch_blocks_strict_result(tmp_path: Path) -> None:
    spec = _spec(tmp_path, expected=0.15, repetitions=1)
    payload = spec.to_dict()
    payload["command"] = ["{python}", "-c", "print('mse:0.1, mae:0.2')"]
    payload["expected_metric_observations"] = 2
    report = OfficialRepoCommandAdapter().run(tmp_path, NativeClaimSpec.from_dict(payload))

    assert report["observation_count_passed"] is False
    assert report["complete_reproduction_allowed"] is False


def test_mtgnn_curated_card_binds_protocol_fields_to_paper_evidence() -> None:
    project = Path(__file__).resolve().parents[1] / "projects" / "finance_agent"
    card = json.loads(
        (project / "method_cards" / "arxiv_2005_11650.json").read_text(encoding="utf-8")
    )
    evidence = {row["section"]: row for row in card["evidence_spans"]}

    protocol_quote = evidence["training_protocol"]["quote"]
    assert evidence["training_protocol"]["source_type"] == "paper"
    assert evidence["hyperparameters"]["source_type"] == "paper"
    assert "Exchange-Rate" in protocol_quote
    assert "60%" in protocol_quote
    assert "10 times" in protocol_quote
    assert "learning rate is 0.001" in protocol_quote
    assert "0.0001" in protocol_quote
    assert evidence["metrics"]["section"] == "metrics"
    assert "0.0349" in evidence["metrics"]["quote"]
