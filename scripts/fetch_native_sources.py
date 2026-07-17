from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from finance_forecast_agent.native_execution import load_native_claim_catalog, sha256_file


def _github_archive_url(repository: str, revision: str) -> str:
    parsed = urlparse(repository)
    parts = parsed.path.strip("/").removesuffix(".git").split("/")
    if parsed.netloc.lower() != "github.com" or len(parts) != 2:
        raise ValueError(f"Only pinned GitHub repositories are supported: {repository}")
    return f"https://codeload.github.com/{parts[0]}/{parts[1]}/zip/{revision}"


def fetch_sources(project_dir: Path, catalog_path: Path, *, verify_only: bool = False) -> None:
    claims = load_native_claim_catalog(catalog_path)
    seen: set[tuple[str, str]] = set()
    for claim in claims:
        identity = (claim.source_repository, claim.source_revision)
        if identity in seen:
            continue
        seen.add(identity)
        archive = project_dir / claim.source_archive_path
        source_root = project_dir / claim.source_root
        archive_ok = archive.exists() and sha256_file(archive) == claim.source_archive_sha256
        source_ok = (
            source_root.exists()
            and (source_root / claim.source_entrypoint).exists()
            and sha256_file(source_root / claim.source_entrypoint) == claim.source_entrypoint_sha256
        )
        if archive_ok and source_ok:
            print(f"verified {claim.model_name}: {claim.source_revision}")
            continue
        if verify_only:
            raise SystemExit(f"missing or drifted source for {claim.model_name}")
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix(".download")
        url = _github_archive_url(claim.source_repository, claim.source_revision)
        print(f"downloading {claim.model_name}: {url}")
        urllib.request.urlretrieve(url, temporary)
        if sha256_file(temporary) != claim.source_archive_sha256:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Downloaded archive hash mismatch for {claim.model_name}")
        temporary.replace(archive)
        if source_root.exists():
            shutil.rmtree(source_root)
        source_root.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as handle:
            handle.extractall(source_root.parent)
        if not source_root.exists() or sha256_file(source_root / claim.source_entrypoint) != claim.source_entrypoint_sha256:
            raise ValueError(f"Extracted source identity mismatch for {claim.model_name}")
        print(f"ready {claim.model_name}: {source_root}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore pinned official repositories for native claims.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("projects/finance_agent/native_claims/catalog.json"),
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    fetch_sources(args.project_dir, args.catalog, verify_only=args.verify_only)


if __name__ == "__main__":
    main()
