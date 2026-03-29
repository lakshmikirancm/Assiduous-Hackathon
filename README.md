# Corporate Finance Autopilot

A weekend hackathon project that pulls public company data from the SEC, runs transparent financial scenarios, and logs every AI agent step so nothing's hidden in a black box. The dashboard lets you ingest a ticker and see the analysis unfold; the API gives you JSON for integration.

**Educational demo, not investment advice.** Always verify numbers in the actual SEC filings before making decisions.

---

## Clone & Get Started

```bash
git clone https://github.com/lakshmikirancm/Assiduous-Hackathon.git
cd Assiduous-Hackathon
```

---

## What This Does

- **Ingest:** Resolves ticker to CIK, fetches official SEC company facts, adds yfinance quotes and light IR text scraping — with retries for rate limits.
- **Store:** SQLite with company profile, financial snapshot, document chunks for RAG, and **agent traces** (every tool call is a queryable row).
- **Scenarios:** 5-year DCF with Base/Upside/Downside — assumptions visible in JSON so you can see what drives the valuation.
- **Agent:** Deterministic tool sequence (load → retrieve docs → run scenarios → get quote → optional LLM narrative). Each step logged, nothing hidden.
- **Output:** Dashboard chart, optional OpenAI advisory, and `/api/.../report` endpoint for an HTML memo.

**Tech:** FastAPI + SQLAlchemy async + SQLite on the backend; Next.js + Recharts on the frontend. Full integration with SEC APIs and yfinance.

---

## Run It Locally

### Backend API

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p data && export PYTHONPATH=.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Dashboard

Open a new terminal:

```bash
cd frontend
npm ci
echo 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000' > .env.local
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) (or 3001 if 3000 is busy). API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

**Optional:** Set `OPENAI_API_KEY` in your environment if you want the advisory to use GPT; otherwise it falls back to deterministic copy.

### Docker

If you have Docker Desktop running:

```bash
docker compose up --build
```

Frontend and API both start automatically. The compose file defaults to `http://127.0.0.1:8000` for the API endpoint so your browser can reach it.

---

## Tests & CI

We split fast (no network) from slow (live SEC, yfinance) so CI doesn't flake.

```bash
# Matches CI: Ruff lint + unit tests + ESLint + production build
make test-ci

# With live SEC and yfinance calls (slower)
cd backend && PYTHONPATH=. pytest -v
```

All 9 tests pass. If SEC or Yahoo rate-limit, just wait a bit and re-run.

---

## Demo (3 Minutes)

**Setup:** Clean local run so you're not fighting rate limits during your presentation.

1. **Why:** "We want auditable steps and cited sources, not a black box answer."
2. **Ingest:** Pick MSFT or a liquid ticker, click **Ingest pipeline**, show SEC + yfinance + optional IR text being pulled.
3. **Profile:** Scroll to see company data (sector, brand summary, financials).
4. **Quote:** Show the auto-refresh quote panel and mention it's delayed from yfinance.
5. **Agent:** Click **Run agent + scenarios**, wait 10s, then:
   - Point to the chart (Base/Upside/Downside enterprise values in billions)
   - Expand a trace step in the JSON viewer to show the tool payloads
   - If using OpenAI, note it's just for narrative wording, not the math
6. **Report:** Open `/docs` or click the report link to show the HTML memo with disclaimers.

---

## API Endpoints

| Method | Path | What It Does |
|--------|------|--------|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/companies/{ticker}/ingest` | Run the full ingest pipeline |
| `GET` | `/api/companies/{ticker}` | Get profile + latest snapshot |
| `GET` | `/api/companies/{ticker}/quote` | Current stock price (delayed) |
| `POST` | `/api/companies/{ticker}/analyze` | Run agent, get scenarios + traces |
| `GET` | `/api/companies/{ticker}/traces` | Retrieve recent agent logs |
| `GET` | `/api/companies/{ticker}/report` | Download HTML investor memo |

All endpoints return JSON and include disclaimers. Swagger UI at `/docs`.

---

## Project Map

```
backend/app/
├── main.py              # 7 endpoints
├── ingest/              # SEC, yfinance, brand, report
├── financial/           # DCF scenarios
├── agent/               # Agent runner + tools
├── rag/                 # Keyword retrieval
├── models/              # ORM (company, trace)
└── schemas/             # Pydantic models

frontend/app/
├── page.tsx             # Main dashboard
├── layout.tsx           # Root layout
└── globals.css          # Dark theme

.github/workflows/
└── ci.yml               # Lint + test + build

tests/                   # 9 total: unit + integration + RAG
```

---

## Known Limits (Not Hiding Anything)

- **yfinance data** is community-maintained and often delayed — always cross-check against SEC for filings.
- **DCF is illustrative** — not a sell-side analysis. Sensitive to WACC and terminal growth assumptions.
- **IR scraping is minimal** — just a few URLs with short timeouts; not a full web crawler.
- **Retrieval is keyword-based** — literal overlap matching, not embeddings. Works fine for the demo.
- **Numbers are examples** — verify everything in the actual 10-K, 10-Q, 8-K.

**Third parties:** SEC ([fair access policy](https://www.sec.gov/os/accessing-edgar-data)), Yahoo Finance via yfinance, optional OpenAI. Read their terms. Set a real `SEC_USER_AGENT` header in `backend/.env`.

---

## What I Learned

The whole point here is **transparency**:
- Public data only, no proprietary feeds.
- Every computation step is logged and queryable.
- Assumptions are explicit (WACC, terminal growth, FCF projections).
- No "magic" LLM blackbox — the agent is a fixed sequence.

This makes the system auditable, reproducible, and actually useful for educational purposes.

---

## License

MIT. Change if your institution requires something else.

---

**Questions?** Check the code — it's heavily commented. Run the tests. or open an issue on GitHub.
