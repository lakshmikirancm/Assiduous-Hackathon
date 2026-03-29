"""Fetch public-facing text from company site (respectful: short timeout, no aggressive crawl)."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:12000]


async def fetch_url_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(
            url,
            headers={"User-Agent": settings.sec_user_agent},
            follow_redirects=True,
            timeout=15.0,
        )
        r.raise_for_status()
        if "text/html" not in (r.headers.get("content-type") or ""):
            return None
        return _clean_text(r.text)
    except Exception:
        return None


async def collect_brand_documents(website: str | None, investor_url: str | None) -> list[tuple[str, str, str]]:
    """Returns list of (title, url, content)."""
    seeds: list[str] = []
    if website:
        w = website if website.startswith("http") else f"https://{website}"
        seeds.append(w.rstrip("/") + "/")
        seeds.append(urljoin(w.rstrip("/") + "/", "investor"))
        seeds.append(urljoin(w.rstrip("/") + "/", "investors"))
    if investor_url:
        seeds.append(investor_url)

    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=20.0) as client:
        for url in seeds:
            host = urlparse(url).netloc
            if url in seen:
                continue
            seen.add(url)
            text = await fetch_url_text(client, url)
            if text and len(text) > 200:
                title = f"Overview ({host})"
                out.append((title, url, text))
            if len(out) >= 2:
                break
    return out
