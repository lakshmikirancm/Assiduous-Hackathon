"""Optional public homepage seeds when vendor metadata omits `website` (e.g. yfinance 429). Not exhaustive."""

PUBLIC_HOME_BY_TICKER: dict[str, str] = {
    "MSFT": "https://www.microsoft.com",
    "AAPL": "https://www.apple.com",
    "GOOGL": "https://abc.xyz",
    "GOOG": "https://abc.xyz",
    "AMZN": "https://www.amazon.com",
    "META": "https://www.meta.com",
    "NVDA": "https://www.nvidia.com",
    "JPM": "https://www.jpmorganchase.com",
}
