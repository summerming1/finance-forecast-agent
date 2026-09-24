from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from .focused_identity import canonical_json, identity
from .focused_state import atomic_json
from .task_queue import LocalTaskQueue, TaskRecord


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def focused_campaign_key(
    *,
    raw_spy_json: str | Path,
    source_metadata: str | Path | None,
    advisor_mode: str,
    rounds: int,
    candidates_per_round: int,
    max_fit_calls: int,
) -> str:
    raw = Path(raw_spy_json)
    payload = {
        "raw_sha256": _sha256(raw),
        "source_sha256": _sha256(Path(source_metadata)) if source_metadata and Path(source_metadata).exists() else None,
        "advisor_mode": advisor_mode,
        "rounds": int(rounds),
        "candidates_per_round": int(candidates_per_round),
        "max_fit_calls": int(max_fit_calls),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]


def submit_focused_campaign(
    queue: LocalTaskQueue,
    *,
    project_dir: str | Path,
    raw_spy_json: str | Path,
    source_metadata: str | Path | None = None,
    advisor_mode: str = "deterministic",
    fixture_dir: str | Path = "projects/finance_agent/llm_fixtures_focused",
    rounds: int = 3,
    candidates_per_round: int = 2,
    max_fit_calls: int = 40,
    start_immediately: bool = True,
    tenant_id: str = "default",
    use_memory_prior: bool = True,
    operation_id: str | None = None,
    research_options: dict[str, Any] | None = None,
    hold: bool = False,
    max_advisor_calls: int = 12,
    max_http_requests: int = 48,
    max_provider_seconds: float = 3600.0,
) -> TaskRecord:
    key = focused_campaign_key(
        raw_spy_json=raw_spy_json,
        source_metadata=source_metadata,
        advisor_mode=advisor_mode,
        rounds=rounds,
        candidates_per_round=candidates_per_round,
        max_fit_calls=max_fit_calls,
    )
    project = Path(project_dir).resolve()
    repo = Path(__file__).resolve().parents[2]
    source = {p.name: _sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    provider = {}
    if advisor_mode == "live":
        from .llm_adapters import OpenAIJsonClient
        client = OpenAIJsonClient()
        provider = client.contract()
    key = identity({"data_request": key, "provider": provider, "project": str(project), "tenant": tenant_id,
                    "memory": use_memory_prior, "source": source, "max_advisor_calls": int(max_advisor_calls), "max_http_requests":int(max_http_requests), "max_provider_seconds":float(max_provider_seconds),
                    "fixture_dir": str(Path(fixture_dir).resolve()), "operation_id": operation_id}, domain="focused-submit-v2")
    options = json.loads(canonical_json(research_options or {}))
    if set(options) - {"input_contract", "starting_baseline", "entry_mode", "change_scope", "allowed_feature_groups", "research_notes", "reviewed_evidence", "replay_call_ids"}:
        raise ValueError("unsupported frozen research options")
    if options:
        key = identity({"request": key, "options": options}, domain="focused-submit-options-v1")
    campaign_id = f"persistent-{key[:24]}"
    command = [
        sys.executable,
        str(repo / "scripts" / "run_focused_spy_campaign.py"),
        "--project-dir",
        str(project),
        "--raw-spy-json",
        str(Path(raw_spy_json).resolve()),
        "--advisor-mode",
        advisor_mode,
        "--fixture-dir",
        str(Path(fixture_dir).resolve()),
        "--rounds",
        str(int(rounds)),
        "--candidates-per-round",
        str(int(candidates_per_round)),
        "--max-fit-calls",
        str(int(max_fit_calls)),
        "--max-advisor-calls", str(int(max_advisor_calls)),
        "--max-http-requests", str(int(max_http_requests)),
        "--max-provider-seconds", str(float(max_provider_seconds)),
        "--campaign-id",
        campaign_id,
        "--resume-existing",
        "--state-db", str(queue.db.path),
        "--tenant-id", tenant_id,
    ]
    if options:
        request_path = project / "requests" / (key + ".json")
        expected = identity(options, domain="focused-options-v1")
        if request_path.exists():
            if identity(json.loads(request_path.read_text()), domain="focused-options-v1") != expected:
                raise ValueError("immutable research request has been modified")
        else:
            atomic_json(request_path, options)
        command.extend(["--request-json", str(request_path), "--request-hash", expected])
    if source_metadata:
        command.extend(["--source-metadata", str(Path(source_metadata).resolve())])
    if not use_memory_prior:
        command.append("--no-memory")
    return queue.submit(
        task_type="focused_campaign",
        command=command,
        cwd=repo,
        result_path=str(project / "focused_campaigns" / campaign_id / "campaign.json"),
        research_context={
            "run_mode": advisor_mode,
            "experiment_type": "forecast_only",
            "data_domain": "us_equity",
            "tenant_id": tenant_id, "project_dir": str(project), "campaign_id": campaign_id, "operation_id": operation_id,
            "expected_source": identity(source, domain="research-execution-source-v1"), "expected_provider": provider,
            "expected_raw_sha256": _sha256(Path(raw_spy_json)),
        },
        start_immediately=start_immediately,
        idempotency_key=f"focused:{key}", hold=hold,
    )


def build_research_package(
    campaign_dir: str | Path,
    out_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    root = Path(campaign_dir)
    if root.is_symlink():
        raise ValueError("package root must not be a symlink")
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    destination = Path(out_dir) if out_dir else root / "research_package"
    destination.mkdir(parents=True, exist_ok=True)
    files, content_bytes = [], {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("package cannot include symlinks")
        if not path.is_file() or destination in path.parents:
            continue
        if root not in path.resolve().parents:
            raise ValueError("package file escapes campaign")
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
        content_bytes[rel] = data
    campaign_path = root / "campaign.json"
    campaign: dict[str, Any] = {}
    if campaign_path.exists():
        campaign = json.loads(content_bytes["campaign.json"])
    elif "campaign.partial.json" in content_bytes:
        campaign = json.loads(content_bytes["campaign.partial.json"])
    index = {
        "schema_version": "focused_research_package_v1",
        "campaign_id": (campaign.get("campaign") or {}).get("campaign_id", root.name),
        "execution_status": campaign.get("execution_status", "partial_or_interrupted"),
        "research_outcome": campaign.get("research_outcome", "inconclusive"),
        "complete_campaign": campaign_path.exists(),
        "files": files,
        "limitations": [
            "package preserves development evidence and does not upgrade exposed data to independent confirmation",
            "missing artifacts remain missing rather than being fabricated",
        ],
    }
    index_path = destination / "research_package.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    zip_path = destination / f"{root.name}.research-package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(index_path, arcname="research_package.json")
        for row in files:
            archive.writestr(row["path"], content_bytes[row["path"]])
    return index_path, zip_path


def load_research_request(path: str | Path | None, expected_hash: str | None) -> dict:
    if path is None:
        return {}
    target = Path(path)
    if not expected_hash or target.is_symlink():
        raise ValueError("research request requires a trusted expected hash and regular file")
    payload = json.loads(target.read_bytes())
    if identity(payload, domain="focused-options-v1") != expected_hash:
        raise ValueError("frozen research request hash mismatch")
    allowed = {"input_contract", "starting_baseline", "entry_mode", "change_scope", "allowed_feature_groups", "research_notes", "reviewed_evidence", "replay_call_ids"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError("unsupported research request fields")
    return payload
