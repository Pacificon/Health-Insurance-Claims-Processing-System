from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings

_engine = None
SessionLocal: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    policy_id: Mapped[str] = mapped_column(String(64), index=True)
    claim_category: Mapped[str] = mapped_column(String(64))
    treatment_date: Mapped[str] = mapped_column(String(16))
    claimed_amount: Mapped[float] = mapped_column(Float)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    trace_json: Mapped[str] = mapped_column(Text)
    submission_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def init_db(database_url: str | None = None) -> None:
    global _engine, SessionLocal
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(_engine)
    SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def reset_db(database_url: str) -> None:
    """Rebind the database — used in tests."""
    init_db(database_url)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_db()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
