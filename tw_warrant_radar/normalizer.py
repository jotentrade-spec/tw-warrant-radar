from __future__ import annotations

import json
from datetime import date
from typing import Any

import pandas as pd
from dateutil import parser


FIELD_ALIASES = {
    "code": ("代號", "證券代號", "權證代號", "有價證券代號", "SecurityCode", "Code", "股票代號"),
    "name": ("名稱", "證券名稱", "權證名稱", "有價證券名稱", "SecurityName", "Name", "股票名稱"),
    "issuer": ("發行券商", "發行人", "發行機構", "Issuer", "Broker", "券商"),
    "close_price": ("收盤價", "最近成交價", "成交價", "Close", "ClosingPrice", "最新成交價"),
    "price_change": ("漲跌", "漲跌價差", "Change", "PriceChange", "ChangePrice"),
    "previous_close_price": ("前日收盤價", "昨收", "PreviousClose", "PreviousClosingPrice", "PrevClose"),
    "bid": ("委買", "委買價", "最佳買價", "買價", "Bid", "BestBidPrice"),
    "ask": ("委賣", "委賣價", "最佳賣價", "賣價", "Ask", "BestAskPrice"),
    "volume": ("成交量", "成交股數", "成交張數", "Volume", "TradeVolume", "TradeVol.", "TradeVol. "),
    "underlying": ("標的", "標的證券", "標的名稱", "Underlying", "UnderlyingSecurity"),
    "strike_price": ("履約價", "履約價格", "Strike", "StrikePrice", "ExercisePrice"),
    "maturity_date": ("到期日", "最後交易日", "存續期間屆滿日", "MaturityDate", "ExpiryDate", "ExpirationDate"),
}


def normalize_records(records: list[dict[str, Any]], source: str, endpoint_url: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    frame = pd.DataFrame(records)
    mapping = infer_mapping(frame.columns)
    normalized = pd.DataFrame()

    for canonical, source_col in mapping.items():
        normalized[canonical] = frame[source_col]

    for canonical in FIELD_ALIASES:
        if canonical not in normalized:
            normalized[canonical] = None

    normalized["source"] = source
    normalized["endpoint_url"] = endpoint_url
    normalized["close_price"] = normalized["close_price"].map(to_number)
    normalized["price_change"] = normalized["price_change"].map(to_number)
    normalized["previous_close_price"] = normalized["previous_close_price"].map(to_number)
    normalized["bid"] = normalized["bid"].map(to_number)
    normalized["ask"] = normalized["ask"].map(to_number)
    normalized["volume"] = normalized["volume"].map(to_number)
    normalized["strike_price"] = normalized["strike_price"].map(to_number)
    normalized["maturity_date"] = normalized["maturity_date"].map(normalize_date)
    normalized["days_to_maturity"] = normalized["maturity_date"].map(days_to_maturity)
    normalized["previous_close_price"] = normalized.apply(resolve_previous_close, axis=1)
    normalized["close_change_pct"] = normalized.apply(resolve_close_change_pct, axis=1)
    normalized["recovery_evidence"] = normalized.apply(resolve_recovery_evidence, axis=1)
    normalized["raw_json"] = pd.Series(records).map(lambda item: json.dumps(item, ensure_ascii=False))

    return normalized


def infer_mapping(columns: pd.Index) -> dict[str, str]:
    normalized_columns = {clean_key(column): str(column) for column in columns}
    mapping: dict[str, str] = {}

    for canonical, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = clean_key(alias)
            if key in normalized_columns:
                mapping[canonical] = normalized_columns[key]
                break
        if canonical in mapping:
            continue

        for clean_column, original_column in normalized_columns.items():
            if any(clean_key(alias) in clean_column for alias in aliases):
                mapping[canonical] = original_column
                break

    return mapping


def clean_key(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        text = str(value).replace(",", "").replace("%", "").strip()
        if text in {"", "--", "-", "----", "N/A", "nan", "None"} or set(text) == {"-"}:
            return None
        return float(text)
    except ValueError:
        return None


def normalize_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if text in {"--", "-", "N/A", "nan"}:
        return ""

    roc_date = parse_roc_date(text)
    if roc_date:
        return roc_date

    try:
        parsed = parser.parse(text, fuzzy=True)
        return parsed.date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return text


def days_to_maturity(value: str) -> int | None:
    if not value:
        return None
    try:
        parsed = parser.parse(value).date()
        return (parsed - date.today()).days
    except (ValueError, TypeError, OverflowError):
        return None


def resolve_previous_close(row: pd.Series) -> float | None:
    previous = row.get("previous_close_price")
    if previous is not None and not pd.isna(previous):
        return previous

    close_price = row.get("close_price")
    price_change = row.get("price_change")
    if close_price is None or price_change is None or pd.isna(close_price) or pd.isna(price_change):
        return None

    previous = close_price - price_change
    return previous if previous > 0 else None


def resolve_close_change_pct(row: pd.Series) -> float | None:
    close_price = row.get("close_price")
    previous = row.get("previous_close_price")
    if close_price is None or previous is None or pd.isna(close_price) or pd.isna(previous) or previous <= 0:
        return None
    return (close_price - previous) / previous


def resolve_recovery_evidence(row: pd.Series) -> str:
    previous = row.get("previous_close_price")
    close_price = row.get("close_price")
    if previous is None or close_price is None or pd.isna(previous) or pd.isna(close_price):
        return "缺前日收盤"
    if close_price > previous:
        return "今日高於前日回收價"
    if close_price == previous:
        return "今日等於前日回收價"
    return "今日低於前日回收價"


def parse_roc_date(text: str) -> str:
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) == 7:
        year = int(digits[:3]) + 1911
        month = int(digits[3:5])
        day = int(digits[5:7])
    elif len(digits) == 6:
        year = int(digits[:2]) + 1911
        month = int(digits[2:4])
        day = int(digits[4:6])
    else:
        return ""

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""
