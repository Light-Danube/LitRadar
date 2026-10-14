"""Explicit public-provider probe; no library, .env, credentials or model access."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
import urllib.error

from sources import venues
from venue_discovery import error_status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='explicitly allow bounded OpenAlex requests')
    parser.add_argument('--venue', default='Computational Linguistics')
    parser.add_argument('--source-id', help='explicitly selected S+digits identity; enables one search page')
    parser.add_argument('--query', default='context')
    parser.add_argument('--year-from', type=int, default=2023)
    parser.add_argument('--year-to', type=int, default=2026)
    args = parser.parse_args(argv)
    if not args.live:
        parser.error('Pass --live to allow provider requests. No requests were made.')
    # Validate the selected search before making any provider request.
    if args.source_id:
        venues.validate_search(args.query, args.source_id, year_from=args.year_from,
                               year_to=args.year_to, limit=5, page=1)
    output = {'checked_at': datetime.now(timezone.utc).isoformat(), 'scope': 'public provider adapter only',
              'no_database_access': True, 'live_search_verified': False}
    try:
        found = venues.lookup_venues(args.venue, limit=5, timeout=8, retries=0, backoff=0)
        output['venues'] = [item.to_dict() for item in found]
        output['status'] = 'ambiguous_venue' if len(found) > 1 else 'ok' if found else 'zero_results'
        if args.source_id:
            chosen = venues.normalize_source_id(args.source_id)
            if chosen not in {item.source_id for item in found}:
                raise ValueError('Chosen source ID was not returned by this bounded lookup')
            result = venues.search_venue(args.query, chosen, year_from=args.year_from,
                                        year_to=args.year_to, limit=5, page=1,
                                        timeout=8, retries=0, backoff=0)
            output.update(status='ok' if result.papers else 'zero_results', live_search_verified=True,
                          selected_source=chosen, count=result.count, truncated=result.truncated,
                          work_ids=[paper.external_id for paper in result.papers], provenance=result.provenance)
        else:
            output['next_step'] = 'Inspect venue identity/ISSNs; rerun with an explicit --source-id to verify search.'
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        output['status'] = error_status(exc)
        # Do not echo provider exception text or authenticated URLs.
        output['error_type'] = type(exc).__name__
        if isinstance(exc, urllib.error.URLError) and 'Tunnel connection failed: 403 Forbidden' in str(exc.reason):
            output['environment_limitation'] = 'proxy_tunnel_http_403'
        output['next_step'] = 'Verify provider access from an allowed network; this result does not establish a provider outage.'
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
