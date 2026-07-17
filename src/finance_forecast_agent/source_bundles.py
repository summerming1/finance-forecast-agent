from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class SourceCandidate:
    paper_id: str
    paper_title: str
    repository: str
    relation: str = "curated_candidate"
    publication_date: str | None = None
    data_status: str = "unknown"
    notes: str = ""


@dataclass(frozen=True)
class SourceBundle:
    paper_id: str
    paper_title: str
    repository: str
    repository_url: str
    relation: str
    identity_status: str
    identity_score: float
    default_branch: str | None
    pinned_commit: str | None
    pinned_commit_date: str | None
    code_license: str | None
    code_license_status: str
    audit_transport: str
    data_status: str
    archived: bool
    blockers: list[str]
    strict_source_ready: bool
    audited_at: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CURATED_SOURCE_CANDIDATES = [
    SourceCandidate(
        "arxiv_2205_13504",
        "Are Transformers Effective for Time Series Forecasting?",
        "cure-lab/LTSF-Linear",
        data_status="repository_dataset_snapshot",
    ),
    SourceCandidate(
        "deeplob_2018",
        "DeepLOB: Deep Convolutional Neural Networks for Limit Order Books",
        "zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books",
        data_status="public_dataset_external_terms",
    ),
    SourceCandidate(
        "rsr_2020",
        "Temporal Relational Ranking for Stock Prediction",
        "fulifeng/Temporal_Relational_Stock_Ranking",
        data_status="repository_processed_snapshot",
    ),
    SourceCandidate(
        "finrl_2020",
        "FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading",
        "AI4Finance-Foundation/FinRL",
        data_status="dynamic_provider_data_not_original_snapshot",
    ),
    SourceCandidate(
        "arxiv_1706_10059",
        "Deep Portfolio Management: A Deep Reinforcement Learning Framework",
        "ZhengyaoJiang/PGPortfolio",
        data_status="repository_market_snapshot_requires_audit",
    ),
    SourceCandidate(
        "arxiv_1904_00745",
        "Deep Learning in Asset Pricing",
        "LouisChen1992/Deep_Learning_in_Asset_Pricing",
        data_status="restricted_crsp_compustat",
    ),
    SourceCandidate(
        "stocknet_2018",
        "Stock Movement Prediction from Tweets and Historical Prices",
        "yumoxu/stocknet-dataset",
        data_status="repository_dataset_snapshot_terms_review_required",
    ),
    SourceCandidate(
        "adv_alstm_2019",
        "Enhancing Stock Movement Prediction with Adversarial Training",
        "fulifeng/Adv-ALSTM",
        data_status="repository_processed_snapshot",
    ),
    SourceCandidate(
        "qlib_platform",
        "Qlib: An AI-oriented Quantitative Investment Platform",
        "microsoft/qlib",
        data_status="dynamic_provider_data_not_original_snapshot",
    ),
    SourceCandidate(
        "fingpt_2023",
        "FinGPT: Open-Source Financial Large Language Models",
        "AI4Finance-Foundation/FinGPT",
        data_status="multiple_external_datasets_require_per_task_audit",
    ),
]


def _tokens(value: str) -> set[str]:
    stop = {"a", "an", "and", "for", "from", "in", "of", "on", "the", "to", "with"}
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in stop
    }


def _identity_score(candidate: SourceCandidate, repository_payload: dict[str, Any]) -> float:
    title_tokens = _tokens(candidate.paper_title)
    repository_text = " ".join(
        str(repository_payload.get(key) or "") for key in ("name", "description", "homepage", "full_name")
    )
    repository_tokens = _tokens(repository_text)
    if not title_tokens:
        return 0.0
    overlap = len(title_tokens & repository_tokens) / len(title_tokens)
    relation_bonus = 0.35 if candidate.relation == "author_confirmed" else 0.15
    return round(min(1.0, overlap + relation_bonus), 3)


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "finance-forecast-agent/0.2",
    }
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_json(session: requests.Session, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = session.get(
        f"{GITHUB_API}/{path.lstrip('/')}",
        params=params,
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list):
        return {"items": payload}
    if not isinstance(payload, dict):
        raise ValueError("GitHub API returned an unsupported payload")
    return payload


def _license_from_text(text: str) -> str | None:
    lowered = text.lower()
    if "apache license" in lowered and "version 2.0" in lowered:
        return "Apache-2.0"
    if "mit license" in lowered or "permission is hereby granted, free of charge" in lowered:
        return "MIT"
    if "gnu general public license" in lowered and "version 3" in lowered:
        return "GPL-3.0"
    if "gnu general public license" in lowered:
        return "GPL"
    if "bsd 3-clause" in lowered or (
        "redistribution and use in source and binary forms" in lowered
        and "neither the name" in lowered
    ):
        return "BSD-3-Clause"
    return None


def _git_fallback(candidate: SourceCandidate, session: requests.Session) -> dict[str, Any]:
    repository_url = f"https://github.com/{candidate.repository}.git"
    result = subprocess.run(
        ["git", "ls-remote", "--symref", repository_url, "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    default_branch = None
    pinned_commit = None
    for line in result.stdout.splitlines():
        if line.startswith("ref: refs/heads/"):
            default_branch = line.split("refs/heads/", 1)[1].split("\t", 1)[0]
        elif line.endswith("\tHEAD"):
            pinned_commit = line.split("\t", 1)[0]
    if not pinned_commit:
        raise ValueError("git ls-remote did not return HEAD")
    branch = default_branch or "main"
    license_key = None
    for name in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"):
        try:
            response = session.get(
                f"https://raw.githubusercontent.com/{candidate.repository}/{branch}/{name}",
                headers={"User-Agent": "finance-forecast-agent/0.2"},
                timeout=15,
            )
            if response.status_code == 200:
                license_key = _license_from_text(response.text)
                if license_key:
                    break
        except requests.RequestException:
            continue
    return {
        "repository": {
            "name": candidate.repository.rsplit("/", 1)[-1],
            "full_name": candidate.repository,
            "description": "",
            "html_url": f"https://github.com/{candidate.repository}",
            "default_branch": default_branch,
            "license": {"spdx_id": license_key} if license_key else None,
            "archived": False,
        },
        "commits": [{"sha": pinned_commit, "commit": {"committer": {"date": None}}}],
    }


def audit_source_candidate(
    candidate: SourceCandidate,
    *,
    session: requests.Session | None = None,
) -> SourceBundle:
    client = session or requests.Session()
    blockers: list[str] = []
    audit_transport = "github_rest_api"
    try:
        repository = _get_json(client, f"repos/{candidate.repository}")
        commit_params = {"per_page": 1}
        if candidate.publication_date:
            commit_params["until"] = candidate.publication_date
        commits = _get_json(client, f"repos/{candidate.repository}/commits", params=commit_params).get("items", [])
    except (requests.RequestException, ValueError, json.JSONDecodeError) as api_exc:
        try:
            fallback = _git_fallback(candidate, client)
            repository = fallback["repository"]
            commits = fallback["commits"]
            audit_transport = "git_remote_and_raw_license_fallback"
            blockers.append(f"GitHub REST audit unavailable: {api_exc}")
            if candidate.publication_date:
                blockers.append("fallback pinned current HEAD, not the publication-date commit")
        except (subprocess.SubprocessError, OSError, ValueError, requests.RequestException) as fallback_exc:
            return SourceBundle(
                paper_id=candidate.paper_id,
                paper_title=candidate.paper_title,
                repository=candidate.repository,
                repository_url=f"https://github.com/{candidate.repository}",
                relation=candidate.relation,
                identity_status="audit_failed",
                identity_score=0.0,
                default_branch=None,
                pinned_commit=None,
                pinned_commit_date=None,
                code_license=None,
                code_license_status="unknown",
                audit_transport="failed",
                data_status=candidate.data_status,
                archived=False,
                blockers=[
                    f"GitHub source audit failed: {api_exc}",
                    f"Git fallback failed: {fallback_exc}",
                ],
                strict_source_ready=False,
                audited_at=datetime.now(timezone.utc).isoformat(),
                notes=candidate.notes,
            )

    score = _identity_score(candidate, repository)
    identity_status = "plausible_needs_human_confirmation" if score >= 0.3 else "weak_match"
    blockers.append("repository-paper identity requires human confirmation")
    if score < 0.3:
        blockers.append("repository metadata has weak title overlap")
    license_key = str((repository.get("license") or {}).get("spdx_id") or "") or None
    license_ok = bool(license_key and license_key not in {"NOASSERTION", "OTHER"})
    if not license_ok:
        blockers.append("repository has no machine-verifiable SPDX license")
    commit = commits[0] if commits else {}
    pinned_commit = str(commit.get("sha") or "") or None
    commit_date = str((((commit.get("commit") or {}).get("committer") or {}).get("date") or "")) or None
    if not pinned_commit:
        blockers.append("no commit could be pinned")
    data_ready = candidate.data_status in {"repository_dataset_snapshot", "repository_processed_snapshot"}
    if not data_ready:
        blockers.append(f"data gate not passed: {candidate.data_status}")
    if repository.get("archived"):
        blockers.append("repository is archived")
    return SourceBundle(
        paper_id=candidate.paper_id,
        paper_title=candidate.paper_title,
        repository=candidate.repository,
        repository_url=str(repository.get("html_url") or f"https://github.com/{candidate.repository}"),
        relation=candidate.relation,
        identity_status=identity_status,
        identity_score=score,
        default_branch=repository.get("default_branch"),
        pinned_commit=pinned_commit,
        pinned_commit_date=commit_date,
        code_license=license_key,
        code_license_status="spdx_identified" if license_ok else "unknown_or_nonstandard",
        audit_transport=audit_transport,
        data_status=candidate.data_status,
        archived=bool(repository.get("archived")),
        blockers=blockers,
        strict_source_ready=False,
        audited_at=datetime.now(timezone.utc).isoformat(),
        notes=candidate.notes,
    )


def audit_curated_sources(output_path: str | Path) -> dict[str, Any]:
    bundles = [audit_source_candidate(candidate) for candidate in CURATED_SOURCE_CANDIDATES]
    payload = {
        "schema_version": "source_bundle_catalog_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(bundles),
        "api_audit_success_count": sum(bundle.identity_status != "audit_failed" for bundle in bundles),
        "strict_source_ready_count": sum(bundle.strict_source_ready for bundle in bundles),
        "human_identity_confirmation_required": sum(
            "repository-paper identity requires human confirmation" in bundle.blockers for bundle in bundles
        ),
        "bundles": [bundle.to_dict() for bundle in bundles],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
