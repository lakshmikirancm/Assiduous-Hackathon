"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyze, getCompany, getQuote, ingest } from "@/lib/api";

type Quote = {
  ticker: string;
  price: number | null;
  currency: string | null;
  market_state: string | null;
  previous_close: number | null;
  source?: string;
};

type FinancialSnapshot = {
  as_of?: string | null;
  revenue_ttm?: number | null;
  net_income_ttm?: number | null;
  total_debt?: number | null;
  cash_and_equivalents?: number | null;
  shares_outstanding?: number | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
};

type CompanyProfile = {
  name?: string | null;
  sector?: string | null;
  industry?: string | null;
  brand_summary?: string | null;
  snapshot?: FinancialSnapshot | null;
  source_urls?: string[];
};

type ScenarioCase = {
  enterprise_value?: number | null;
};

type ScenarioSet = {
  base: ScenarioCase;
  upside: ScenarioCase;
  downside: ScenarioCase;
  limitations?: string[];
};

type Advisory = {
  summary?: string;
  options_discussion?: string[];
};

type TraceStep = {
  step_index: number;
  step_type: string;
  payload: Record<string, unknown>;
};

type AgentAnalysis = {
  run_id: string;
  scenarios?: ScenarioSet;
  advisory?: Advisory;
  traces?: TraceStep[];
};

type Op = "ingest" | "load" | "analyze";

function errMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rs = s % 60;
  if (m > 0) return `${m}m ${rs}s`;
  return `${rs}s`;
}

function useElapsed(active: boolean): number {
  const [ms, setMs] = useState(0);
  useEffect(() => {
    if (!active) {
      setMs(0);
      return;
    }
    const t0 = Date.now();
    const id = window.setInterval(() => setMs(Date.now() - t0), 200);
    return () => window.clearInterval(id);
  }, [active]);
  return ms;
}

const OP_COPY: Record<Op, { title: string; sub: string }> = {
  ingest: {
    title: "Ingesting public data",
    sub: "SEC EDGAR (CIK + facts), market snapshot, optional IR page text. Often 15–60s if vendors rate-limit.",
  },
  load: {
    title: "Loading company profile",
    sub: "Reading the saved record from the app database.",
  },
  analyze: {
    title: "Running analysis pipeline",
    sub: "Tools: company bundle → retrieval → DCF scenarios → quote → advisory. With OpenAI, allow ~20–90s.",
  },
};

export default function Page() {
  const [ticker, setTicker] = useState("MSFT");
  const [op, setOp] = useState<Op | null>(null);
  const [quoteBusy, setQuoteBusy] = useState(false);
  const [quoteSyncing, setQuoteSyncing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [analysis, setAnalysis] = useState<AgentAnalysis | null>(null);
  const [useLlm, setUseLlm] = useState(true);

  const busy = op !== null;
  const elapsed = useElapsed(busy);

  const refreshQuote = useCallback(
    async (silent: boolean) => {
      if (silent) setQuoteSyncing(true);
      else setQuoteBusy(true);
      try {
        if (!silent) setErr(null);
        const q = await getQuote(ticker);
        setQuote(q);
      } catch (e: unknown) {
        if (!silent) setErr(errMessage(e));
      } finally {
        if (silent) setQuoteSyncing(false);
        else setQuoteBusy(false);
      }
    },
    [ticker],
  );

  useEffect(() => {
    refreshQuote(false).catch(() => {});
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      refreshQuote(true).catch(() => {});
    }, 20000);
    return () => window.clearInterval(id);
  }, [refreshQuote]);

  const loadCompany = async () => {
    setOp("load");
    setErr(null);
    try {
      const c = await getCompany(ticker);
      setCompany(c);
    } catch (e: unknown) {
      setErr(errMessage(e));
    } finally {
      setOp(null);
    }
  };

  const runIngest = async () => {
    setOp("ingest");
    setErr(null);
    try {
      await ingest(ticker);
      const c = await getCompany(ticker);
      setCompany(c);
    } catch (e: unknown) {
      setErr(errMessage(e));
    } finally {
      setOp(null);
    }
  };

  const runAnalyze = async () => {
    setOp("analyze");
    setErr(null);
    try {
      const a = await analyze(ticker, useLlm);
      setAnalysis(a);
    } catch (e: unknown) {
      setErr(errMessage(e));
    } finally {
      setOp(null);
    }
  };

  const manualQuote = () => {
    setErr(null);
    refreshQuote(false).catch(() => {});
  };

  const chartData = useMemo(() => {
    if (!analysis?.scenarios) return [];
    const s = analysis.scenarios;
    const ev = (x: ScenarioCase) => (x?.enterprise_value ? x.enterprise_value / 1e9 : 0);
    return [
      { name: "Base", ev: ev(s.base) },
      { name: "Upside", ev: ev(s.upside) },
      { name: "Downside", ev: ev(s.downside) },
    ];
  }, [analysis]);

  const overlay = op ? OP_COPY[op] : null;

  return (
    <>
      {busy && overlay && (
        <div className="loading-overlay" role="alertdialog" aria-busy="true" aria-live="polite">
          <div className="loading-card">
            <div className="spinner spinner-lg" style={{ marginBottom: 16 }} />
            <p className="loading-title">{overlay.title}</p>
            <p className="loading-sub">{overlay.sub}</p>
            <div className="progress-track" aria-hidden>
              <div className="progress-bar" />
            </div>
            <p className="loading-time">Elapsed: {formatElapsed(elapsed)} — you can leave this tab open.</p>
          </div>
        </div>
      )}

      <main className="shell">
        <header className="topbar">
          <div>
            <span className="badge">
              <span style={{ color: "var(--accent2)" }}>●</span> Demo · not advice
            </span>
            <h1 className="title">Corporate Finance Autopilot</h1>
            <p className="lead">
              Ingest public filings &amp; market context, run transparent Base / Upside / Downside scenarios, and inspect
              every agent step. Always verify numbers in primary SEC filings.
            </p>
          </div>
        </header>

        <section className="grid2">
          <div className="card">
            <div className="card-label">Ticker · US listing</div>
            <div className="row">
              <input
                className="input"
                value={ticker}
                disabled={busy}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                aria-label="Stock ticker symbol"
              />
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={runIngest}
              >
                {op === "ingest" ? <span className="spinner" aria-hidden /> : null}
                Ingest pipeline
              </button>
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={loadCompany}>
                {op === "load" ? <span className="spinner" aria-hidden /> : null}
                Load profile
              </button>
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={useLlm}
                disabled={busy}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              <span>
                LLM advisory (needs <code>OPENAI_API_KEY</code> on API; falls back if unset)
              </span>
            </label>
            {err && <div className="error-box">{err}</div>}
          </div>

          <div className="card">
            <div className="card-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span>Market quote</span>
              <span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 500 }}>
                {quoteSyncing ? "Syncing…" : quoteBusy ? "Loading…" : "Auto-refresh ~20s"}
              </span>
            </div>
            {quoteBusy || !quote ? (
              <div style={{ marginTop: 14 }}>
                <div className="skeleton" style={{ height: 36, width: "55%" }} />
                <div className="skeleton" style={{ height: 14, width: "75%", marginTop: 12 }} />
                <div className="skeleton" style={{ height: 14, width: "40%", marginTop: 10 }} />
              </div>
            ) : (
              <>
                <div className="quote-price">
                  {quote.price != null ? `${quote.currency || "$"} ${quote.price.toFixed(2)}` : "—"}
                </div>
                <div className="quote-meta">
                  Prev close: {quote.previous_close != null ? quote.previous_close.toFixed(2) : "—"} ·{" "}
                  {quote.market_state || "—"}
                </div>
              </>
            )}
            <div className="caveat">
              {quote?.source || "Vendor data may be delayed; not a guaranteed real-time feed."}
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <button type="button" className="btn btn-ghost" disabled={busy || quoteBusy} onClick={manualQuote}>
                {quoteBusy ? <span className="spinner" aria-hidden /> : null}
                Refresh quote now
              </button>
            </div>
          </div>
        </section>

        {company && (
          <section style={{ marginTop: 16 }}>
            <div className="card">
              <div className="section-title">{company.name}</div>
              <p className="section-sub">
                {company.sector} · {company.industry}
              </p>
              <p style={{ margin: 0, lineHeight: 1.6, color: "#c5cedc" }}>{company.brand_summary}</p>
              <div style={{ marginTop: 16 }}>
                <div className="card-label">Snapshot (mixed sources)</div>
                <pre className="mono-block">{JSON.stringify(company.snapshot, null, 2)}</pre>
              </div>
              <div style={{ marginTop: 16 }}>
                <div className="card-label">Sources</div>
                <ul className="sources">
                  {(company.source_urls || []).map((u: string) => (
                    <li key={u}>
                      <a href={u} target="_blank" rel="noreferrer">
                        {u}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                style={{ marginTop: 16 }}
                onClick={runAnalyze}
              >
                {op === "analyze" ? <span className="spinner" aria-hidden /> : null}
                Run agent + scenarios + advisory
              </button>
            </div>
          </section>
        )}

        {analysis && (
          <section className="grid-analysis" style={{ marginTop: 16 }}>
            <div className="card" style={{ minHeight: 320 }}>
              <div className="section-title">Scenario enterprise value (illustrative)</div>
              <p className="section-sub">DCF-style band — inputs and formulas are returned by the API for review.</p>
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#243041" />
                    <XAxis dataKey="name" stroke="#8b98a8" />
                    <YAxis
                      stroke="#8b98a8"
                      tickFormatter={(v) => `${v}`}
                      label={{ value: "USD bn", angle: -90, position: "insideLeft", fill: "#8b98a8" }}
                    />
                    <Tooltip
                      contentStyle={{ background: "#101722", border: "1px solid var(--border)" }}
                      formatter={(v: number) => [`${v.toFixed(2)} bn`, "EV"]}
                    />
                    <Bar dataKey="ev" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 8, lineHeight: 1.45 }}>
                {analysis.scenarios?.limitations?.join(" ")}
              </p>
            </div>

            <div className="card">
              <div className="section-title">Advisory (non-binding)</div>
              <p style={{ lineHeight: 1.55, marginTop: 8 }}>{analysis.advisory?.summary}</p>
              <div className="card-label" style={{ marginTop: 14 }}>
                Strategic / funding options (discussion)
              </div>
              <ul className="sources">
                {(analysis.advisory?.options_discussion || []).map((x: string, i: number) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>

            <div className="card" style={{ gridColumn: "1 / -1" }}>
              <div className="section-title">Agent trace · run {analysis.run_id}</div>
              <p className="section-sub">Each step is persisted — no single opaque prompt.</p>
              <div style={{ display: "grid", gap: 10 }}>
                {(analysis.traces || []).map((t: TraceStep) => (
                  <div key={t.step_index} className="trace-block">
                    <div className="trace-type">{t.step_type}</div>
                    <pre className="mono-block" style={{ marginTop: 8, marginBottom: 0, background: "transparent", border: "none", padding: 0 }}>
                      {JSON.stringify(t.payload, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        <footer
          style={{
            marginTop: 48,
            paddingTop: 24,
            borderTop: "1px solid var(--border)",
            color: "var(--muted)",
            fontSize: 13,
            lineHeight: 1.65,
          }}
        >
          <span style={{ color: "var(--text)", fontWeight: 600 }}>API</span>
          {" · "}
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            OpenAPI (/docs)
          </a>
          {" · "}
          <a
            href={`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/companies/${encodeURIComponent(ticker)}/report`}
            target="_blank"
            rel="noreferrer"
          >
            HTML memorandum
          </a>
          <span style={{ opacity: 0.85 }}> (ingest first)</span>
        </footer>
      </main>
    </>
  );
}
