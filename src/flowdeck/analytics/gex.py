"""Dealer gamma exposure (GEX) analytics.

Convention used here (the common one):
  - dealers are assumed long calls sold to them? No - dealers are SHORT the
    options customers are LONG. Net effect for the standard model:
    call gamma counts positive, put gamma counts negative.
  - GEX per contract = gamma * open_interest * 100 * spot^2 * 0.01
    i.e. dollar gamma per 1% move in the underlying.

This is a model, not ground truth. It assumes customer long calls / long puts
against dealer books, which breaks down around heavy call overwriting. Good
enough to find the walls that matter on SPY/QQQ.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CONTRACT_MULT = 100


def compute_gex(chain: pd.DataFrame, spot: float) -> pd.DataFrame:
    """Net GEX per strike from a chain snapshot.

    chain columns required: strike, contract_type ('call'|'put'), gamma, oi
    Returns a frame indexed by strike with call_gex, put_gex, net_gex (dollars
    per 1% move).
    """
    df = chain.dropna(subset=["gamma", "oi"]).copy()
    df = df[df["oi"] > 0]

    dollar_gamma = df["gamma"] * df["oi"] * CONTRACT_MULT * spot**2 * 0.01
    sign = np.where(df["contract_type"].str.lower() == "put", -1.0, 1.0)
    df["gex"] = dollar_gamma * sign

    out = (
        df.pivot_table(index="strike", columns="contract_type", values="gex", aggfunc="sum")
        .rename(columns={"call": "call_gex", "put": "put_gex"})
        .fillna(0.0)
    )
    out["net_gex"] = out.sum(axis=1)
    return out.sort_index()


def zero_gamma_level(gex_by_strike: pd.DataFrame) -> float | None:
    """Interpolated strike where cumulative net GEX flips sign.

    Below this level dealers are net short gamma (they chase moves, vol
    expands). Above it they are long gamma (they fade moves, price pins).
    """
    cum = gex_by_strike["net_gex"].cumsum()
    signs = np.sign(cum.values)
    flips = np.where(np.diff(signs) != 0)[0]
    if len(flips) == 0:
        return None
    i = flips[0]
    k0, k1 = cum.index[i], cum.index[i + 1]
    v0, v1 = cum.iloc[i], cum.iloc[i + 1]
    if v1 == v0:
        return float(k0)
    # linear interpolation between the two strikes
    return float(k0 + (k1 - k0) * (0 - v0) / (v1 - v0))


def gamma_walls(gex_by_strike: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top-n strikes by absolute net GEX. These act like magnets/repellents
    depending on which side of zero gamma we are trading."""
    ranked = gex_by_strike.reindex(
        gex_by_strike["net_gex"].abs().sort_values(ascending=False).index
    )
    return ranked.head(n)


def gex_profile(chain: pd.DataFrame, spot: float, n_walls: int = 5) -> dict:
    """One-call summary used by the agent tools and the dashboard."""
    by_strike = compute_gex(chain, spot)
    zg = zero_gamma_level(by_strike)
    walls = gamma_walls(by_strike, n_walls)
    total = float(by_strike["net_gex"].sum())
    return {
        "spot": spot,
        "total_net_gex": total,
        "regime": "long_gamma" if (zg is not None and spot > zg) else "short_gamma",
        "zero_gamma": zg,
        "walls": [
            {"strike": float(k), "net_gex": float(v)}
            for k, v in walls["net_gex"].items()
        ],
    }
