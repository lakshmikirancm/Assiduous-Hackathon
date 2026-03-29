"""Lightweight retrieval over ingested text — keyword overlap (no embeddings required for baseline)."""

from __future__ import annotations

import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import CompanyDocument


def _tokenize(q: str) -> set[str]:
    return {w for w in re.split(r"\W+", q.lower()) if len(w) > 2}


async def retrieve_snippets(
    session: AsyncSession,
    company_id: int,
    query: str,
    k: int = 5,
) -> list[str]:
    result = await session.execute(
        select(CompanyDocument).where(CompanyDocument.company_id == company_id)
    )
    docs = result.scalars().all()
    if not docs:
        return []
    q_tokens = _tokenize(query)
    if not q_tokens:
        return [d.content[:600] for d in docs[:k]]

    scored: list[tuple[float, str]] = []
    for d in docs:
        c_tokens = _tokenize(d.content)
        overlap = sum((Counter(q_tokens) & Counter(c_tokens)).values())
        scored.append((float(overlap), d.content[:1200]))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for score, s in scored[:k] if score > 0]
    return top if top else [s for _, s in scored[:k]]
