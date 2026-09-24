"""Explicit trusted-local-operator review of an existing MethodCard/source version.

Never invoked by the Advisor. No download or automatic approval is performed.
The review JSON contains source paths relative to --project and explicit use/rights.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.focused_literature import approve_research_literature, revoke_research_literature


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    actions = parser.add_subparsers(dest='action',required=True)
    approve = actions.add_parser('approve')
    approve.add_argument('--review-json',type=Path,required=True)
    approve.add_argument('--confirm-source-reviewed',action='store_true',required=True)
    revoke = actions.add_parser('revoke')
    revoke.add_argument('--review-id',required=True)
    revoke.add_argument('--reviewer',required=True)
    revoke.add_argument('--reason',required=True)
    args = parser.parse_args()
    if args.action == 'approve':
        if args.review_json.is_symlink() or args.review_json.stat().st_size > 200_000:
            raise ValueError('review request must be a bounded regular local JSON file')
        values=json.loads(args.review_json.read_text(encoding='utf-8'))
        result=approve_research_literature(args.project,**values)
        print(json.dumps({'review_id':result['review_id'],'purpose':'research',
            'simulation_only':result['simulation_only'],'strict_reproduction_not_implied':True}))
    else:
        revoke_research_literature(args.project,args.review_id,reviewer=args.reviewer,reason=args.reason)
        print(json.dumps({'review_id':args.review_id,'status':'revoked'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
