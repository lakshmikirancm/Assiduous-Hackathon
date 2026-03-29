from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.datetime_utils import utc_now


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    cik: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(256), nullable=True)
    brand_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    positioning_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list as string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    snapshots: Mapped[list["FinancialSnapshot"]] = relationship(back_populates="company")
    documents: Mapped[list["CompanyDocument"]] = relationship(back_populates="company")


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company_profiles.id"), index=True)
    as_of: Mapped[str | None] = mapped_column(String(32), nullable=True)
    revenue_ttm: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_income_ttm: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_and_equivalents: Mapped[float | None] = mapped_column(Float, nullable=True)
    shares_outstanding: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_facts_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    company: Mapped["CompanyProfile"] = relationship(back_populates="snapshots")


class CompanyDocument(Base):
    """Chunkable text for RAG / reporting (ingested from public pages)."""

    __tablename__ = "company_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("company_profiles.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    company: Mapped["CompanyProfile"] = relationship(back_populates="documents")
