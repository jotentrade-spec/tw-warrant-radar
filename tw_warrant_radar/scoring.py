from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScoreResult:
    score: float
    reasons: str


def score_row(row: pd.Series) -> ScoreResult:
    score = 0.0
    reasons: list[str] = []
    close_price = safe_float(row.get("close_price"))
    bid = safe_float(row.get("bid"))
    ask = safe_float(row.get("ask"))
    volume = safe_float(row.get("volume"))
    days = safe_int(row.get("days_to_maturity"))
    previous_close = safe_float(row.get("previous_close_price"))
    close_change_pct = safe_float(row.get("close_change_pct"))

    if close_price is not None and close_price <= 0.02:
        score += 35
        reasons.append("價格 <= 0.02")
    elif close_price is not None and close_price <= 0.05:
        score += 15
        reasons.append("價格 <= 0.05")

    if bid is not None and bid >= 0.01:
        score += 30
        reasons.append("委買 >= 0.01")

    if ask is not None and ask > 0:
        score += 12
        reasons.append("委賣存在")

    if volume is not None and volume > 0:
        score += 10
        reasons.append("成交量存在")

    if bid is not None and ask is not None and bid > 0 and ask >= bid:
        spread = (ask - bid) / ((ask + bid) / 2)
        if spread <= 0.2:
            score += 10
            reasons.append("bid/ask 價差小")
        elif spread <= 0.5:
            score += 4
            reasons.append("bid/ask 價差可接受")

    if days is not None and days >= 10:
        score += 10
        reasons.append("剩餘天數 >= 10")
    elif days is not None and days < 5:
        score -= 10
        reasons.append("剩餘天數過短")

    if previous_close is not None:
        score += 6
        reasons.append("有前日回收參考價")
        if close_change_pct is not None and close_change_pct > 0:
            score += 4
            reasons.append("今日高於前日回收價")

    return ScoreResult(score=max(score, 0), reasons="；".join(reasons))


def apply_scores(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    results = frame.apply(score_row, axis=1)
    frame = frame.copy()
    frame["market_maker_score"] = results.map(lambda item: item.score)
    frame["score_reasons"] = results.map(lambda item: item.reasons)
    return frame.sort_values("market_maker_score", ascending=False)


def safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
