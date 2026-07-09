from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    method: Mapped[str] = mapped_column(String(8), default="GET")
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float] = mapped_column(Float, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WarrantScan(Base):
    __tablename__ = "warrant_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    endpoint_url: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(Text, default="")
    issuer: Mapped[str] = mapped_column(Text, default="")
    close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_close_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    close_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    recovery_evidence: Mapped[str] = mapped_column(Text, default="")
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    underlying: Mapped[str] = mapped_column(Text, default="")
    strike_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    maturity_date: Mapped[str] = mapped_column(String(32), default="")
    days_to_maturity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_maker_score: Mapped[float] = mapped_column(Float, default=0)
    score_reasons: Mapped[Text] = mapped_column(Text, default="")
    raw_json: Mapped[Text] = mapped_column(Text, default="")


if settings.database_url.startswith("sqlite:///"):
    sqlite_path = settings.database_url.replace("sqlite:///", "", 1)
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    ensure_schema_columns()


def ensure_schema_columns() -> None:
    inspector = inspect(engine)
    if "warrant_scans" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("warrant_scans")}
    additions = {
        "previous_close_price": "FLOAT",
        "close_change_pct": "FLOAT",
        "recovery_evidence": "TEXT DEFAULT ''",
    }
    with engine.begin() as connection:
        for column, column_type in additions.items():
            if column not in existing:
                connection.execute(text(f"ALTER TABLE warrant_scans ADD COLUMN {column} {column_type}"))
