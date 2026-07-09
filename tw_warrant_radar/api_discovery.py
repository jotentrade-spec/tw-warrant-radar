from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import requests

from .config import settings


WARRANT_KEYWORDS = (
    "權證",
    "認購",
    "認售",
    "warrant",
    "call warrant",
    "put warrant",
)

FALLBACK_ENDPOINTS = {
    "TWSE": [
        "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX",
        "https://openapi.twse.com.tw/v1/opendata/t187ap35_L",
        "https://openapi.twse.com.tw/v1/opendata/t187ap36_L",
        "https://openapi.twse.com.tw/v1/opendata/t187ap37_L",
        "https://openapi.twse.com.tw/v1/opendata/t187ap38_L",
    ],
    "TPEX": [
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
    ],
}


@dataclass(frozen=True)
class DiscoveredEndpoint:
    source: str
    url: str
    method: str = "GET"
    title: str = ""
    description: str = ""
    score: float = 0


def discover_all() -> list[DiscoveredEndpoint]:
    endpoints: list[DiscoveredEndpoint] = []
    endpoints.extend(discover_from_swagger("TWSE", settings.twse_swagger_url))
    endpoints.extend(discover_from_swagger("TPEX", settings.tpex_swagger_url))

    seen = {endpoint.url for endpoint in endpoints}
    for source, urls in FALLBACK_ENDPOINTS.items():
        for url in urls:
            if url not in seen:
                endpoints.append(DiscoveredEndpoint(source=source, url=url, title="fallback candidate", score=1))

    return sorted(endpoints, key=lambda item: item.score, reverse=True)


def discover_from_swagger(source: str, swagger_url: str) -> list[DiscoveredEndpoint]:
    try:
        response = requests.get(swagger_url, timeout=settings.request_timeout)
        response.raise_for_status()
        swagger = response.json()
    except requests.RequestException:
        return []

    base_url = infer_base_url(swagger_url, swagger)
    paths = swagger.get("paths", {})
    endpoints: list[DiscoveredEndpoint] = []

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, meta in methods.items():
            if method.lower() != "get" or not isinstance(meta, dict):
                continue
            title = str(meta.get("summary") or meta.get("operationId") or "")
            description = str(meta.get("description") or "")
            searchable = " ".join([path, title, description]).lower()
            score = endpoint_keyword_score(searchable)
            if score <= 0:
                continue
            endpoints.append(
                DiscoveredEndpoint(
                    source=source,
                    url=urljoin(base_url, path.lstrip("/")),
                    method=method.upper(),
                    title=title,
                    description=description,
                    score=score,
                )
            )

    return endpoints


def infer_base_url(swagger_url: str, swagger: dict) -> str:
    servers = swagger.get("servers")
    if isinstance(servers, list) and servers:
        server_url = servers[0].get("url")
        if server_url:
            return server_url.rstrip("/") + "/"

    if swagger_url.endswith("swagger.json"):
        return swagger_url[: -len("swagger.json")]
    return swagger_url.rsplit("/", 1)[0] + "/"


def endpoint_keyword_score(text: str) -> float:
    score = 0.0
    for keyword in WARRANT_KEYWORDS:
        if keyword.lower() in text:
            score += 5 if keyword in ("權證", "warrant") else 2
    if "買賣" in text or "行情" in text or "成交" in text:
        score += 1.5
    return score
