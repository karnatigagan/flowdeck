"""Options chain snapshot ingestion (Polygon.io).

One job: pull the full chain for a symbol, flatten it to rows, hand it to the
DB layer. Raw responses get kept so the analytics can be recomputed later if
my math conventions change.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

BASE = "https://api.polygon.io"
MAX_DTE = 45  # expiries beyond this are noise for what I trade


class PolygonChains:
    def __init__(self, api_key: str | None = None):
        self.key = api_key or os.environ["POLYGON_API_KEY"]
        self.http = httpx.Client(timeout=30)

    def fetch_chain(self, underlying: str) -> pd.DataFrame:
        """Full snapshot for one underlying, paginated, out to MAX_DTE."""
        cutoff = (datetime.now(timezone.utc) + timedelta(days=MAX_DTE)).date()
        url = f"{BASE}/v3/snapshot/options/{underlying}"
        params = {"limit": 250, "expiration_date.lte": str(cutoff), "apiKey": self.key}
        rows: list[dict] = []
        while url:
            r = self.http.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
            rows.extend(self._flatten(c) for c in payload.get("results", []))
            url = payload.get("next_url")
            params = {"apiKey": self.key}  # next_url carries the rest
        df = pd.DataFrame(rows)
        df["snapshot_ts"] = datetime.now(timezone.utc)
        df["underlying"] = underlying
        return df

    @staticmethod
    def _flatten(c: dict) -> dict:
        details = c.get("details", {})
        greeks = c.get("greeks", {})
        day = c.get("day", {})
        quote = c.get("last_quote", {})
        return {
            "ticker": details.get("ticker"),
            "expiry": details.get("expiration_date"),
            "strike": details.get("strike_price"),
            "contract_type": details.get("contract_type"),
            "oi": c.get("open_interest"),
            "volume": day.get("volume"),
            "iv": c.get("implied_volatility"),
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
        }


if __name__ == "__main__":
    # smoke test: python -m flowdeck.ingest.chains
    chain = PolygonChains().fetch_chain("SPY")
    print(chain.shape)
    print(chain.head(10).to_string())
