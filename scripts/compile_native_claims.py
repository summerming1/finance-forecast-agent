from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.native_claim_compiler import (
    compile_native_claim_catalog,
    compile_native_claim_draft,
    export_native_claim_specs,
    save_native_claim_draft,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--bootstrap-existing", action="store_true")
    parser.add_argument("--draft-paper")
    args = parser.parse_args()
    catalog = args.project_dir / "native_claims" / "catalog.json"
    specs = args.project_dir / "native_claims" / "specs"
    if args.bootstrap_existing:
        paths = export_native_claim_specs(catalog, specs)
        print(f"Exported {len(paths)} native claim specs to {specs}")
    if args.draft_paper:
        draft = compile_native_claim_draft(args.project_dir, args.draft_paper)
        path = save_native_claim_draft(args.project_dir, draft)
        print(
            f"Drafted {draft.claim_id}: ready={draft.ready_for_approval}; "
            f"blockers={len(draft.blockers)}; path={path}"
        )
    if not args.draft_paper:
        result = compile_native_claim_catalog(specs, catalog)
        print(f"Compiled {result['claim_count']} native claims from {specs}")


if __name__ == "__main__":
    main()
