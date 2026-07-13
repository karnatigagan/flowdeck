# flowdeck

Options market structure copilot. Pulls full options chains on a schedule, computes dealer gamma exposure (GEX) and fair value gaps, and puts an LLM agent on top so I can ask things like "why is SPY pinned at 620 today" and get an answer backed by actual chain data instead of vibes.

## why

I trade SPY options and got tired of juggling five tabs to answer basic structure questions: one site for gamma levels, TradingView for marking FVGs by hand, another screener for IV rank. None of them talk to each other and none of them can explain *why* a level matters. flowdeck pulls it all into one pipeline with an agent that can actually reason over it.

## what it does (building toward)

- snapshots full SPY/QQQ chains on a schedule into Postgres, so open interest and IV *changes* are queryable, not just current state
- net GEX by strike, zero-gamma level, gamma wall detection
- fair value gap detection on intraday candles, with fill tracking and confluence scoring against gamma levels (an unfilled FVG sitting on a gamma wall is a very different trade than one in no-mans-land)
- IV rank / percentile and put-call skew
- an agent with read-only tools over all of the above. it explains, screens, and alerts. it does not place trades - execution stays human, on purpose
- signal log + hit-rate tracking so the system has a measured track record instead of anecdotes

## stack

Python, FastAPI, Postgres (Timescale), Polygon.io for chain data, React dashboard later. See docs/PLAN.md for the build phases.

## status

Early. Ingestion and the core analytics (GEX + FVG) land first, agent layer after.
