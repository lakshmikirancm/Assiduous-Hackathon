"""Tests for keyword retrieval."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import CompanyDocument, CompanyProfile
from app.rag.retrieve import retrieve_snippets


@pytest.mark.asyncio
async def test_retrieve_prefers_overlap(session: AsyncSession):
    p = CompanyProfile(ticker="TST", cik="0000000001", name="Test Co")
    session.add(p)
    await session.flush()
    session.add(
        CompanyDocument(
            company_id=p.id,
            title="a",
            source_url="https://example.com/a",
            content="Cloud revenue growth and enterprise strategy for the next decade.",
        )
    )
    session.add(
        CompanyDocument(
            company_id=p.id,
            title="b",
            source_url="https://example.com/b",
            content="Lorem ipsum boilerplate text without useful tokens.",
        )
    )
    await session.commit()

    out = await retrieve_snippets(session, p.id, "revenue cloud strategy enterprise", k=2)
    assert len(out) >= 1
    assert "cloud" in out[0].lower()


@pytest.mark.asyncio
async def test_retrieve_empty_docs(session: AsyncSession):
    p = CompanyProfile(ticker="EMP", cik="0000000002", name="Empty")
    session.add(p)
    await session.flush()
    await session.commit()
    assert await retrieve_snippets(session, p.id, "anything", k=3) == []
