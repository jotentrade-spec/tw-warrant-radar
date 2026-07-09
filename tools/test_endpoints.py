from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tw_warrant_radar.api_discovery import discover_all
from tw_warrant_radar.normalizer import infer_mapping, normalize_records
import requests

from tw_warrant_radar.config import settings
from tw_warrant_radar.scanner import fetch_endpoint


def main() -> int:
    parser = argparse.ArgumentParser(description="Test TWSE/TPEX warrant endpoints and inferred field mapping.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum endpoints to test.")
    args = parser.parse_args()

    endpoints = discover_all()[: args.limit]
    if not endpoints:
        print("No candidate endpoints discovered.")
        return 1

    for index, endpoint in enumerate(endpoints, start=1):
        print(f"\n[{index}] {endpoint.source} score={endpoint.score:.1f}")
        print(endpoint.url)
        try:
            response = requests.get(endpoint.url, timeout=settings.request_timeout)
            print(f"http={response.status_code} content_type={response.headers.get('content-type', '')}")
            if response.status_code >= 400:
                print(response.text[:300])
        except requests.RequestException as exc:
            print(f"http_error={exc}")
            continue

        records = fetch_endpoint(endpoint)
        print(f"records={len(records)}")

        if not records:
            continue

        columns = list(records[0].keys())
        mapping = infer_mapping(columns)
        print("columns=", ", ".join(columns[:30]))
        print("mapping=", mapping)

        normalized = normalize_records(records[:20], endpoint.source, endpoint.url)
        print("normalized_rows=", len(normalized))
        if not normalized.empty:
            preview_cols = ["code", "name", "issuer", "close_price", "bid", "ask", "volume", "underlying", "strike_price", "maturity_date"]
            print(normalized[preview_cols].head(3).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
