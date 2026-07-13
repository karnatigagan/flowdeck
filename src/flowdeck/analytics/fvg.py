"""Fair value gap detection + confluence with gamma levels.

An FVG is a 3-candle imbalance:
  bullish: candle[i].low  > candle[i-2].high  -> gap zone (high[i-2], low[i])
  bearish: candle[i].high < candle[i-2].low   -> gap zone (high[i], low[i-2])

Price tends to revisit these zones. The edge (if any) comes from context:
an unfilled FVG sitting on a big gamma wall is a much more interesting level
than one floating in no-mans-land, so confluence scoring is the point here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class FVG:
    kind: str            # 'bullish' | 'bearish'
    top: float
    bottom: float
    created_at: pd.Timestamp
    filled: bool = False
    filled_at: pd.Timestamp | None = None
    fill_pct: float = 0.0  # how much of the zone has been traded through
    tags: list[str] = field(default_factory=list)

    @property
    def mid(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def size(self) -> float:
        return self.top - self.bottom


def detect_fvgs(candles: pd.DataFrame, min_size: float = 0.0) -> list[FVG]:
    """candles: index=timestamp, columns high/low. Returns gaps in time order."""
    highs = candles["high"].values
    lows = candles["low"].values
    ts = candles.index
    out: list[FVG] = []
    for i in range(2, len(candles)):
        if lows[i] > highs[i - 2]:  # bullish imbalance
            gap = FVG("bullish", top=lows[i], bottom=highs[i - 2], created_at=ts[i])
            if gap.size >= min_size:
                out.append(gap)
        elif highs[i] < lows[i - 2]:  # bearish imbalance
            gap = FVG("bearish", top=lows[i - 2], bottom=highs[i], created_at=ts[i])
            if gap.size >= min_size:
                out.append(gap)
    return out


def track_fills(gaps: list[FVG], candles: pd.DataFrame) -> list[FVG]:
    """Mark gaps filled once price trades fully through the zone (after creation).
    Partial fills recorded as fill_pct so the agent can talk about them."""
    for gap in gaps:
        after = candles[candles.index > gap.created_at]
        if after.empty:
            continue
        if gap.kind == "bullish":
            # fill = price trading back DOWN through the zone
            lowest = after["low"].min()
            gap.fill_pct = min(1.0, max(0.0, (gap.top - lowest) / gap.size))
            if lowest <= gap.bottom:
                gap.filled = True
                gap.filled_at = after[after["low"] <= gap.bottom].index[0]
        else:
            highest = after["high"].max()
            gap.fill_pct = min(1.0, max(0.0, (highest - gap.bottom) / gap.size))
            if highest >= gap.top:
                gap.filled = True
                gap.filled_at = after[after["high"] >= gap.top].index[0]
    return gaps


def score_confluence(gaps: list[FVG], levels: dict[str, float], tol_pct: float = 0.15) -> list[FVG]:
    """Tag gaps that overlap notable structure levels.

    levels: name -> price, e.g. {'zero_gamma': 618.4, 'wall_620': 620.0}
    tol_pct: distance (as % of price) that still counts as confluence.
    """
    for gap in gaps:
        for name, px in levels.items():
            if px is None:
                continue
            tol = px * tol_pct / 100
            if gap.bottom - tol <= px <= gap.top + tol:
                gap.tags.append(name)
    return gaps


def open_gaps(gaps: list[FVG]) -> list[FVG]:
    return [g for g in gaps if not g.filled]
