from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import requests
from sqlalchemy import delete

from .api_discovery import DiscoveredEndpoint, discover_all
from .config import settings
from .models import ApiEndpoint, SessionLocal, WarrantScan, init_db
from .normalizer import normalize_records
from .scoring import apply_scores


def refresh_api_catalog() -> list[DiscoveredEndpoint]:
    init_db()
    endpoints = discover_all()
    with SessionLocal() as session:
        session.execute(delete(ApiEndpoint))
        for endpoint in endpoints:
            session.add(
                ApiEndpoint(
                    source=endpoint.source,
                    url=endpoint.url,
                    method=endpoint.method,
                    title=endpoint.title,
                    description=endpoint.description,
                    score=endpoint.score,
                    last_seen_at=datetime.utcnow(),
                )
            )
        session.commit()
    return endpoints


def scan_market(limit_endpoints: int | None = None) -> pd.DataFrame:
    init_db()
    endpoints = refresh_api_catalog()
    if limit_endpoints:
        endpoints = endpoints[:limit_endpoints]

    frames: list[pd.DataFrame] = []
    for endpoint in endpoints:
        records = fetch_endpoint(endpoint)
        if not records:
            continue
        frame = normalize_records(records[: settings.max_endpoint_rows], endpoint.source, endpoint.url)
        if frame.empty:
            continue
        frame = frame[frame["code"].notna()]
        frame = frame[frame["code"].astype(str).str.strip() != ""]
        if not frame.empty:
            frames.append(frame)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    enriched = merge_by_code(combined)
    enriched = refresh_recovery_evidence(enriched)
    scored = apply_scores(enriched)
    persist_scan(scored)
    return scored


def fetch_endpoint(endpoint: DiscoveredEndpoint) -> list[dict[str, Any]]:
    payload = fetch_endpoint_payload(endpoint.url)
    if payload is None:
        return []

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("data", "result", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def fetch_endpoint_payload(url: str) -> Any | None:
    try:
        response = requests.get(url, timeout=settings.request_timeout)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def persist_scan(frame: pd.DataFrame) -> None:
    if frame.empty:
        return

    scanned_at = datetime.utcnow()
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            WarrantScan(
                scanned_at=scanned_at,
                source=to_text(row.get("source")),
                endpoint_url=to_text(row.get("endpoint_url")),
                code=to_text(row.get("code")),
                name=to_text(row.get("name")),
                issuer=to_text(row.get("issuer")),
                close_price=to_float(row.get("close_price")),
                previous_close_price=to_float(row.get("previous_close_price")),
                close_change_pct=to_float(row.get("close_change_pct")),
                recovery_evidence=to_text(row.get("recovery_evidence")),
                bid=to_float(row.get("bid")),
                ask=to_float(row.get("ask")),
                volume=to_float(row.get("volume")),
                underlying=to_text(row.get("underlying")),
                strike_price=to_float(row.get("strike_price")),
                maturity_date=to_text(row.get("maturity_date")),
                days_to_maturity=to_int(row.get("days_to_maturity")),
                market_maker_score=to_float(row.get("market_maker_score")) or 0,
                score_reasons=to_text(row.get("score_reasons")),
                raw_json=to_text(row.get("raw_json")),
            )
        )

    with SessionLocal() as session:
        session.add_all(rows)
        session.commit()


def merge_by_code(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "code" not in frame:
        return frame

    rows = []
    for code, group in frame.groupby("code", dropna=True, sort=False):
        if not str(code).strip():
            continue
        merged = {"code": code}
        for column in group.columns:
            if column == "code":
                continue
            merged[column] = first_useful_value(group[column])
        rows.append(merged)

    return pd.DataFrame(rows)


def refresh_recovery_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    frame = frame.copy()
    for column in ("close_price", "price_change", "previous_close_price"):
        if column not in frame:
            frame[column] = None

    frame["previous_close_price"] = frame.apply(resolve_previous_close_after_merge, axis=1)
    frame["close_change_pct"] = frame.apply(resolve_close_change_pct_after_merge, axis=1)
    frame["recovery_evidence"] = frame.apply(resolve_recovery_evidence_after_merge, axis=1)
    return frame


def resolve_previous_close_after_merge(row: pd.Series) -> float | None:
    previous = to_float(row.get("previous_close_price"))
    if previous is not None:
        return previous

    close_price = to_float(row.get("close_price"))
    price_change = to_float(row.get("price_change"))
    if close_price is None or price_change is None:
        return None

    previous = close_price - price_change
    return previous if previous > 0 else None


def resolve_close_change_pct_after_merge(row: pd.Series) -> float | None:
    close_price = to_float(row.get("close_price"))
    previous = to_float(row.get("previous_close_price"))
    if close_price is None or previous is None or previous <= 0:
        return None
    return (close_price - previous) / previous


def resolve_recovery_evidence_after_merge(row: pd.Series) -> str:
    close_price = to_float(row.get("close_price"))
    previous = to_float(row.get("previous_close_price"))
    if close_price is None or previous is None:
        return "缺前日收盤"
    if close_price > previous:
        return "今日高於前日回收價"
    if close_price == previous:
        return "今日等於前日回收價"
    return "今日低於前日回收價"


def first_useful_value(series: pd.Series):
    for value in series:
        if value is None:
            continue
        if isinstance(value, float) and pd.isna(value):
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def latest_scan(limit: int = 100) -> list[WarrantScan]:
    init_db()
    with SessionLocal() as session:
        latest_at = session.query(WarrantScan.scanned_at).order_by(WarrantScan.scanned_at.desc()).limit(1).scalar()
        if latest_at is None:
            return []
        return (
            session.query(WarrantScan)
            .filter(WarrantScan.scanned_at == latest_at)
            .order_by(WarrantScan.market_maker_score.desc())
            .limit(limit)
            .all()
        )


def api_catalog() -> list[ApiEndpoint]:
    init_db()
    with SessionLocal() as session:
        return session.query(ApiEndpoint).order_by(ApiEndpoint.score.desc(), ApiEndpoint.source.asc()).all()


def to_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def to_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
