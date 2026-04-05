"""
Financial collector — market data via yfinance + FRED macro via requests.
OpenBB is the preferred path; yfinance is the zero-config fallback used here for MVP.
"""
from datetime import datetime, timedelta
from typing import List
import requests

import yfinance as yf

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config, get_secret


class FinancialCollector(BaseCollector):
    name = "financial"

    def collect(self) -> List[IntelItem]:
        cfg = get_config()["collectors"]["financial"]
        items = []
        items.extend(self._collect_tickers(cfg["tickers"]))
        items.extend(self._collect_macro(cfg.get("macro_series", [])))
        return items

    def _collect_tickers(self, tickers: list) -> List[IntelItem]:
        items = []
        for symbol in tickers:
            try:
                t = yf.Ticker(symbol)
                hist = t.fast_info
                price = getattr(hist, "last_price", None)
                prev = getattr(hist, "previous_close", None)
                if price is None or prev is None:
                    continue
                pct = ((price - prev) / prev) * 100
                severity = Severity.HIGH if abs(pct) >= 3 else Severity.MEDIUM if abs(pct) >= 1 else Severity.INFO
                direction = "up" if pct > 0 else "down"
                items.append(IntelItem(
                    domain=Domain.FINANCIAL,
                    source="yfinance",
                    title=f"{symbol} {direction} {abs(pct):.2f}%",
                    summary=f"{symbol} is trading at ${price:.2f}, {direction} {abs(pct):.2f}% from previous close of ${prev:.2f}.",
                    url=f"https://finance.yahoo.com/quote/{symbol}",
                    published_at=datetime.utcnow(),
                    severity=severity,
                    tags=[symbol, "market", "equities"],
                    confidence=0.95,
                ))
            except Exception as e:
                print(f"[financial] ticker {symbol} error: {e}")
        return items

    def _collect_macro(self, series_ids: list) -> List[IntelItem]:
        items = []
        fred_key = get_secret("FRED_API_KEY")
        if not fred_key:
            return items

        series_names = {
            "FEDFUNDS": "Federal Funds Rate",
            "CPIAUCSL": "CPI (Inflation)",
            "UNRATE": "Unemployment Rate",
        }

        for series_id in series_ids:
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/series/observations"
                    f"?series_id={series_id}&api_key={fred_key}&file_type=json"
                    f"&sort_order=desc&limit=2"
                )
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                obs = resp.json().get("observations", [])
                if len(obs) < 2:
                    continue
                latest = float(obs[0]["value"])
                prior = float(obs[1]["value"])
                change = latest - prior
                name = series_names.get(series_id, series_id)
                items.append(IntelItem(
                    domain=Domain.FINANCIAL,
                    source="FRED",
                    title=f"{name}: {latest:.2f}% (changed {change:+.2f}%)",
                    summary=f"Latest {name} reading is {latest:.2f}%, compared to prior reading of {prior:.2f}%.",
                    url=f"https://fred.stlouisfed.org/series/{series_id}",
                    published_at=datetime.utcnow(),
                    severity=Severity.MEDIUM if abs(change) > 0.1 else Severity.INFO,
                    tags=[series_id, "macro", "fred"],
                    confidence=1.0,
                ))
            except Exception as e:
                print(f"[financial] FRED {series_id} error: {e}")
        return items
