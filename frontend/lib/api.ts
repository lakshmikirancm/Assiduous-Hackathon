const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function ingest(ticker: string) {
  const r = await fetch(`${API}/api/companies/${encodeURIComponent(ticker)}/ingest`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getCompany(ticker: string) {
  const r = await fetch(`${API}/api/companies/${encodeURIComponent(ticker)}`, { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getQuote(ticker: string) {
  const r = await fetch(`${API}/api/companies/${encodeURIComponent(ticker)}/quote`, { cache: "no-store" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function analyze(ticker: string, includeLlm: boolean) {
  const r = await fetch(`${API}/api/companies/${encodeURIComponent(ticker)}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ include_llm_narrative: includeLlm }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
