import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    twse_swagger_url: str = os.getenv("TWSE_SWAGGER_URL", "https://openapi.twse.com.tw/v1/swagger.json")
    tpex_swagger_url: str = os.getenv("TPEX_SWAGGER_URL", "https://www.tpex.org.tw/openapi/swagger.json")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///instance/warrant_radar.sqlite3")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))
    max_endpoint_rows: int = int(os.getenv("MAX_ENDPOINT_ROWS", "2000"))


settings = Settings()
