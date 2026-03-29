"""HTML report generator for investor presentation."""

from datetime import datetime, timezone
from app.schemas.api import AgentAnalyzeResponse, CompanyOut


def generate_html_report(company: CompanyOut, analysis: AgentAnalyzeResponse) -> str:
    """Generate a single-page HTML investor report."""
    ticker = company.ticker
    name = company.name or ticker
    sector = company.sector or "Unknown"
    snap = company.snapshot
    scenarios = analysis.scenarios
    advisory = analysis.advisory

    # Format financials
    revenue_str = f"${snap.revenue_ttm / 1e9:.2f}B" if snap and snap.revenue_ttm else "—"
    ni_str = f"${snap.net_income_ttm / 1e9:.2f}B" if snap and snap.net_income_ttm else "—"
    debt_str = f"${snap.total_debt / 1e9:.2f}B" if snap and snap.total_debt else "—"
    cash_str = f"${snap.cash_and_equivalents / 1e9:.2f}B" if snap and snap.cash_and_equivalents else "—"

    # Scenario values
    base_ev = scenarios.base.enterprise_value
    upside_ev = scenarios.upside.enterprise_value
    downside_ev = scenarios.downside.enterprise_value
    base_eps = scenarios.base.equity_per_share
    upside_eps = scenarios.upside.equity_per_share
    downside_eps = scenarios.downside.equity_per_share

    base_ev_str = f"${base_ev / 1e9:.2f}B" if base_ev else "—"
    upside_ev_str = f"${upside_ev / 1e9:.2f}B" if upside_ev else "—"
    downside_ev_str = f"${downside_ev / 1e9:.2f}B" if downside_ev else "—"
    base_eps_str = f"${base_eps:.2f}" if base_eps else "—"
    upside_eps_str = f"${upside_eps:.2f}" if upside_eps else "—"
    downside_eps_str = f"${downside_eps:.2f}" if downside_eps else "—"

    # Scenario rows
    base_equity_val_str = f"${scenarios.base.equity_value / 1e9:.2f}B" if scenarios.base.equity_value else "—"
    upside_equity_val_str = f"${scenarios.upside.equity_value / 1e9:.2f}B" if scenarios.upside.equity_value else "—"
    downside_equity_val_str = f"${scenarios.downside.equity_value / 1e9:.2f}B" if scenarios.downside.equity_value else "—"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} ({ticker}) - Investment Memorandum</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Roboto, -apple-system, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #0c3d91; margin: 0 0 10px; }}
        h2 {{ color: #0c3d91; margin: 30px 0 15px; border-bottom: 2px solid #0c3d91; padding-bottom: 5px; }}
        h3 {{ color: #444; margin: 20px 0 10px; }}
        .header {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }}
        .info-box {{ background: #f5f5f5; padding: 15px; border-radius: 4px; }}
        .info-item {{ margin: 8px 0; }}
        .label {{ color: #666; font-size: 0.85em; text-transform: uppercase; font-weight: 600; }}
        .value {{ font-size: 1.1em; color: #222; font-weight: 500; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background: #0c3d91;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f9f9f9; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }}
        .metric-card {{
            background: #f0f8ff;
            padding: 15px;
            border-left: 4px solid #0c3d91;
            border-radius: 4px;
        }}
        .metric-card .metric-title {{ font-weight: 600; color: #666; font-size: 0.9em; }}
        .metric-card .metric-value {{ font-size: 1.5em; color: #0c3d91; font-weight: 700; margin-top: 5px; }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            color: #856404;
        }}
        .disclaimer {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
            color: #721c24;
        }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.85em;
            color: #999;
        }}
        .scenario-row {{ padding: 8px 12px; }}
        .scenario-base {{ background: #e8f4f8; }}
        .scenario-upside {{ background: #d4f1e4; }}
        .scenario-downside {{ background: #f1d4d4; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{name} ({ticker})</h1>
        <p><em>Investment Memorandum | Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</em></p>

        <div class="header">
            <div class="info-box">
                <div class="info-item">
                    <div class="label">Sector</div>
                    <div class="value">{sector}</div>
                </div>
                <div class="info-item">
                    <div class="label">Industry</div>
                    <div class="value">{company.industry or 'N/A'}</div>
                </div>
                <div class="info-item">
                    <div class="label">CIK</div>
                    <div class="value">{company.cik or 'N/A'}</div>
                </div>
            </div>
            <div class="info-box">
                <div class="label" style="margin-bottom: 8px;">Latest Financial Snapshot (TTM)</div>
                <table style="margin: 0;">
                    <tr><td style="border: none; padding: 4px 0;"><strong>Revenue</strong></td><td style="border: none; padding: 4px 0; text-align: right;">{revenue_str}</td></tr>
                    <tr><td style="border: none; padding: 4px 0;"><strong>Net Income</strong></td><td style="border: none; padding: 4px 0; text-align: right;">{ni_str}</td></tr>
                    <tr><td style="border: none; padding: 4px 0;"><strong>Total Debt</strong></td><td style="border: none; padding: 4px 0; text-align: right;">{debt_str}</td></tr>
                    <tr><td style="border: none; padding: 4px 0;"><strong>Cash</strong></td><td style="border: none; padding: 4px 0; text-align: right;">{cash_str}</td></tr>
                </table>
            </div>
        </div>

        <h2>Company Overview</h2>
        <p>{company.brand_summary or 'No summary available.'}</p>
        {f'<h3>Positioning Notes</h3><p>{company.positioning_notes}</p>' if company.positioning_notes else ''}

        <h2>DCF Valuation (Base / Upside / Downside)</h2>
        <table>
            <thead>
                <tr>
                    <th>Scenario</th>
                    <th>Enterprise Value</th>
                    <th>Equity Value</th>
                    <th>Equity Per Share</th>
                    <th>WACC</th>
                    <th>Terminal Growth</th>
                </tr>
            </thead>
            <tbody>
                <tr class="scenario-base">
                    <td><strong>Base</strong></td>
                    <td>{base_ev_str}</td>
                    <td>{base_equity_val_str}</td>
                    <td>{base_eps_str}</td>
                    <td>{scenarios.base.assumptions.get('wacc', 'N/A')}</td>
                    <td>{scenarios.base.assumptions.get('terminal_growth', 'N/A')}</td>
                </tr>
                <tr class="scenario-upside">
                    <td><strong>Upside</strong></td>
                    <td>{upside_ev_str}</td>
                    <td>{upside_equity_val_str}</td>
                    <td>{upside_eps_str}</td>
                    <td>{scenarios.upside.assumptions.get('wacc', 'N/A')}</td>
                    <td>{scenarios.upside.assumptions.get('terminal_growth', 'N/A')}</td>
                </tr>
                <tr class="scenario-downside">
                    <td><strong>Downside</strong></td>
                    <td>{downside_ev_str}</td>
                    <td>{downside_equity_val_str}</td>
                    <td>{downside_eps_str}</td>
                    <td>{scenarios.downside.assumptions.get('wacc', 'N/A')}</td>
                    <td>{scenarios.downside.assumptions.get('terminal_growth', 'N/A')}</td>
                </tr>
            </tbody>
        </table>

        <div class="warning">
            <strong>Model Assumptions:</strong>
            <ul>
                {''.join(f'<li>{note}</li>' for note in scenarios.formula_notes)}
            </ul>
        </div>

        <h2>Advisory & Strategic Considerations</h2>
        <p><strong>{advisory.summary}</strong></p>
        
        <h3>Funding & Strategic Options</h3>
        <ul>
            {''.join(f'<li>{opt}</li>' for opt in advisory.options_discussion)}
        </ul>

        <h3>Key Risks & Uncertainties</h3>
        <ul>
            {''.join(f'<li>{risk}</li>' for risk in advisory.risks_and_uncertainties)}
        </ul>

        <h3>Data Gaps & Limitations</h3>
        <ul>
            {''.join(f'<li>{gap}</li>' for gap in advisory.data_gaps)}
            {''.join(f'<li>{lim}</li>' for lim in scenarios.limitations)}
        </ul>

        <h2>Data Sources</h2>
        <ul>
            <li><strong>Financial Data:</strong> SEC EDGAR (official company filings)</li>
            <li><strong>Market Data:</strong> yfinance (community-maintained; verify against official sources)</li>
            <li><strong>Company Positioning:</strong> Official company website and investor relations pages</li>
        </ul>

        <div class="disclaimer">
            <strong>DISCLAIMER:</strong> This memorandum is for educational purposes only and does not constitute investment advice.
            The valuations, projections, and recommendations herein are illustrative and based on publicly available data
            with inherent limitations. All figures should be independently verified against primary SEC filings and current market data.
            Any investment decision should be made in consultation with qualified financial advisors and legal counsel.
        </div>

        <div class="footer">
            <p>
                <strong>Generated by Corporate Finance Autopilot</strong><br>
                Run ID: {analysis.run_id}<br>
            </p>
        </div>
    </div>
</body>
</html>"""
    return html
