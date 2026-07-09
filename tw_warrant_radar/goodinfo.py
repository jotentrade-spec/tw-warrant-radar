from __future__ import annotations

import re
from urllib.parse import quote


GOODINFO_HOME = "https://goodinfo.tw/tw/"


def stock_id_from_text(value: str | None) -> str:
    if not value:
        return ""
    match = re.search(r"\b\d{4,6}\b", str(value))
    return match.group(0) if match else ""


def goodinfo_stock_url(value: str | None) -> str:
    stock_id = stock_id_from_text(value)
    if stock_id:
        return f"{GOODINFO_HOME}StockDetail.asp?STOCK_ID={stock_id}"
    if value:
        return f"{GOODINFO_HOME}StockList.asp?MARKET_CAT=%E5%85%A8%E9%83%A8&INDUSTRY_CAT={quote(str(value))}"
    return GOODINFO_HOME
