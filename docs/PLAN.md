# build plan

Working notes for myself. Order matters here - analytics are useless without good snapshots, and the agent is useless without good analytics.

## phase 0 - scaffolding [done]

repo, plan, deps, gitignore

## phase 1 - ingestion

- [ ] Polygon client: full chain snapshot for SPY (all expiries out 45 days)
- [ ] schema: chain_snapshots(ts, symbol, expiry, strike, contract_type, oi, volume, iv, delta, gamma, bid, ask)
- [ ] 1m/5m candle ingestion for the underlying (needed for FVG detection)
- [ ] snapshot cadence: every 15 min during RTH, one EOD full pull
- [ ] keep raw responses in cold storage so I can recompute if my math changes

## phase 2 - analytics

- [ ] gex.py: net gamma exposure per strike. convention: dealers long calls / short puts, so call gamma positive, put gamma negative. GEX = gamma * OI * 100 * spot^2 * 0.01 (dollar gamma per 1% move)
- [ ] zero-gamma level via sign flip interpolation
- [ ] gamma walls: top-N absolute GEX strikes
- [ ] fvg.py: 3-candle fair value gaps (bullish: low[i] > high[i-2], bearish: high[i] < low[i-2]), fill tracking, and confluence scoring vs gamma levels
- [ ] iv_rank.py: IV rank + percentile over trailing 252d

## phase 3 - agent

- [ ] tool registry: get_gex_profile, get_fvgs, get_iv_rank, get_unusual_volume, get_positions (read-only)
- [ ] FastAPI endpoints wrapping analytics
- [ ] system prompt: explain structure with numbers, never advise position sizing
- [ ] hard rule: no order placement tools. execution is manual, always

## phase 4 - alerts + dashboard

- [ ] price-approaching-level alerts (gamma wall, zero gamma, unfilled FVG)
- [ ] React dash: GEX profile chart front and center, FVG overlay on price

## phase 5 - evals

- [ ] log every flagged signal with context snapshot
- [ ] forward returns at 1h/4h/1d after each signal
- [ ] hit-rate report. if the signals do not beat coin flips, say so in the README

## decisions

- broker access read-only. an agent with order permissions is a liability, and human-in-the-loop is the better story anyway
- Polygon over scraping. paying for clean data beats fighting rate limits
- Postgres over anything fancier until it hurts
