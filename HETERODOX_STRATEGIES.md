# Heterodox Strategies

Signal-generation studies grounded in heterodox economic analytical toolkits — Marxian, Post-Keynesian, Kaleckian, world-systems — layered on stratum's typed event timeline and versioned semantic label store. Marxism is used as a *pragmatic analytical school*, not a political stance (Dengist "whichever cat catches the mouse" framing). The edge is analytical: lenses that mainstream quant desks under-use.

All six strategies live inside stratum's existing discipline:

- **Two-clock store** (`event_time`, `knowledge_time`) — no signal is computed from data that wasn't knowable on the decision date.
- **Semantic labels are versioned data** — every LLM classification records `classifier_version`, `prompt_hash`, `model_id`, evidence, confidence. Studies pin a version.
- **Studies are pre-registered YAML configs** — event classes declared before the run.
- **No execution paths.** Order placement lives in a sibling repo (working name `stratum-trader`). Stratum only produces signals and validates them against realized returns / event-contract settlements.

## Build order

1. **#3 Reserve-army tracker** — FRED/ALFRED only, no LLM. Cleanest to stand up (~2 days). Introduces the `macro_series` table and the FRED/ALFRED ingester — substrate for #4 and part of #7A.
2. **#4 Overaccumulation macro regime** — same FRED/ALFRED ingester, adds Fed Z.1 buybacks/dividends and PNFI. No fanout in the initial signal.
3. **#1 Consensus fade (FOMC first)** — introduces the `articles` table + news RSS ingesters + LLM `article_sentiment` classifier. Unlocks #2 and #6.
4. **#2 Class-weighted sentiment** — zero-marginal-cost overlay on #1 once labor-press RSS is added.
5. **#7A Commodity + geopolitics (Layer A)** — sanctions/chokepoint/reshoring indices on the commodity universe. Starts `descriptive_only` until a commodity factor model is added.
6. **#6 Policy dispersion** — think-tank RSS + `policy_stance` classifier + new `prediction_market_prices` store table (scraped Kalshi/PredictIt historical).
7. **#7B analytical add-ons** — three more label classes (rerouting stage, frontier extraction, semi-periphery beneficiary) once #7A is live.

## What lives in the sibling repo (execution)

- Signal → order-payload translators for IBKR MCP, Robinhood MCP, ForecastEx event contracts.
- Alpaca paper-trading harness for pre-live validation of every signal.
- Position-tracking, PnL, account-summary reads.

Nothing in the execution repo contributes back to stratum. Stratum is read-only, always.

---

## #3 — Reserve army of labor → CPI/rate regime conditioning

**Premise.** Marx's reserve army of labor (unemployed/underemployed workers as wage-discipline mechanism) is the analytical ancestor of NAIRU/Phillips-curve reasoning. When the reserve thins, capital's bargaining power weakens → margin compression and inflation persistence — both of which the mainstream inflation-print consensus tends to underweight in tightening cycles.

**Stratum surface.**

- Store: new `macro_series` table (grain: `series_id × observation_date × vintage_date`). ALFRED supplies real `knowledge_time` via `realtime_start`/`realtime_end`.
- Universe: no per-instrument requirement. Conditioning variable overlays on any equity study.
- Study: `studies/reserve_army_regime_earnings_conditioning.yaml` — conditions Study A pooled earnings SCAR on reserve-tightness regime.
- Ingest: `ingest/specs/fred_series_alfred.yaml` — U6RATE, LNS11300060, JTSQUR, ECIWAG, OPHNFB.

**Signal.** Weighted composite of 10y rolling z-scores across the five series, computed with vintage-aware ALFRED data at each observation date. Top decile = `thin_reserve`; bottom decile = `slack_reserve`.

**Study.** Pre-registered classes: `earnings_beat_thin_reserve`, `earnings_beat_slack_reserve`, `earnings_miss_thin_reserve`, `earnings_miss_slack_reserve`. Hypothesis: mean SCAR post-earnings differs by regime because margin/labor-cost sensitivity is regime-dependent.

**Kill risks.** COVID structural break in the labor market — split-sample pre/post 2020. Small N per regime cell if 4-quadrant analysis is required.

**Execution home.** Sibling repo trades CPI-above-X on ForecastEx + longs in labor-cost-sensitive tickers (EAT, DRI, MAN, RHI) when the composite fires.

---

## #4 — Overaccumulation / falling-rate-of-profit macro regime

**Premise.** Marxian crisis theory: capital accumulates faster than profitable outlets absorb it; financialization (buybacks, dividends) displaces reinvestment; margins compress; crisis follows. Overlaps with the Kaleckian profit equation and Minskyan financial-instability frames — reason to trust the shape of the signal even if the causal story is contested.

**Stratum surface.**

- Store: adds a handful of FRED series to `macro_series` (`CP`, `NFCPATAX`, `PNFI`, Fed Z.1 buybacks/dividends). No per-name fundamentals fanout in the initial pass.
- Universe: `universe_macro.yaml` (SPY/QQQ/TLT/GLD as regime-conditioning event-study targets).
- Study: `studies/overaccumulation_macro_regime.yaml`.
- Ingest: shares `fred_series_alfred.yaml` with #3.

**Signal.** `financialization_ratio = (buybacks + dividends) / capex`. Aggregate corporate profit growth + margin z-score. Regime = top decile of financialization ratio AND falling profit growth for 2+ consecutive quarters.

**Study.** Pre-registered classes: `regime_high_financialization_falling_profit`, `regime_high_financialization_rising_profit`, `regime_normal`. Hypothesis: forward 6m/12m SPY returns are lower conditional on the first class.

**Kill risks.** False positives in long expansions (2011/2015/2018 fired without imminent recession). Confirm with yield-curve inversion as a secondary conditioning variable. Signal is macro-cycle — study horizons in months, not days.

**Execution home.** Sibling repo takes VIX futures long or QQQ put spreads on regime confirmation.

**Deferred to Phase 2.** Per-name screening (high-financialization / low-capex candidates for individual put spreads) requires either the 30-name bench (selection bias — semis have been the strongest margin story of the cycle) or a full S&P 500 fundamentals fanout. Neither is required for the macro-regime signal to work; both are optional richer follow-ons.

---

## #1 — Consensus fade (narrative-saturation mean reversion)

**Premise.** Different economic actors sit in different circuits of capital (money-capital, productive-capital, consumption — Marx's M–C–P–C′–M′ schema). Financial press oversamples money-capital's viewpoint and undersamples productive-capital and consumption/labor signals. Not conspiracy — structural informational asymmetry. Creates predictable blind spots when sentiment saturates around macro releases.

**Stratum surface.**

- Store: new `articles` table (`id`, `source`, `title`, `url`, `published_at`, `knowledge_time`, `body_hash`, `outlet_class`). New `article_labels` table (grain: `article_id × classifier_version`) with `sentiment`, `confidence`, `circuit`, evidence span. `events.type` gains `macro_release` (subtype ∈ {fomc, cpi, nfp, gdp, pce}).
- Universe: `universe_macro.yaml`.
- Study: `studies/consensus_fade_fomc.yaml`.
- Ingest: `ingest/specs/news_capital_press.yaml` — WSJ, Bloomberg, FT, Reuters RSS.

**Signal.** For each event window `[event−7d, event−0d]`: `uniformity = 1 − entropy(sentiment_over_articles)`. `money_capital_skew = fraction tagged circuit=money`. Signal fires when `uniformity > 2σ` rolling AND `money_capital_skew > 0.7`.

**Study.** Pre-registered classes: `high_uniformity_hawkish`, `high_uniformity_dovish`, `low_uniformity`. Hypothesis: mean SCAR on SPY/TLT `[0, +3d]` fades the pre-event sentiment sign for the two high-uniformity classes.

**Kill risks.** Small sample (≈8 FOMC/yr, ≈12 CPI/yr). LLM scoring drift — mitigated by `classifier_version` pinning. Start with FOMC only (cleanest event, richest coverage).

**Execution home.** Sibling repo trades ForecastEx event contracts on the fade direction.

---

## #2 — Class-position-weighted sentiment (overlay on #1)

**Premise.** Different outlets sit in different material positions (ownership, ad-base, subscriber demographic) which surface different information. Divergence between capital-press and labor-press sentiment on the same event is a two-sided sentiment signal that filters #1's false positives.

**Stratum surface.**

- Store: shares `articles` and `article_labels` tables with #1. `outlet_class ∈ {capital, labor, mixed}` classified at ingest based on outlet metadata.
- Universe: `universe_macro.yaml`.
- Study: `studies/class_sentiment_overlay.yaml` — trades only when #1 fires AND `|sentiment_gap| > 1σ`.
- Ingest: `ingest/specs/news_labor_press.yaml` — Jacobin, In These Times, EPI, major union press releases, r/antiwork via Reddit archive.

**Signal.** `sentiment_gap = mean(sentiment | outlet_class=capital) − mean(sentiment | outlet_class=labor)`.

**Study.** Overlay on #1's pre-registered classes; secondary partition by `gap_direction`.

**Kill risks.** Labor press cadence is irregular — dropouts on many macro events. Best on macro-labor events (BLS releases, min-wage/tariff-impact debates), not FOMC.

**Execution home.** Same as #1.

---

## #7 — Commodity + imperialism (strongest)

Layer A is the mechanical pipeline. Layer B is three Marxian-lens semantic label classes that add differentiated analytical edge.

### Layer A — chokepoint, sanctions, reshoring indices

**Stratum surface.**

- Store: new tables `sanctions_events` (`event_time`, `source_agency`, `target_entity`, `target_commodity`, `action`, `url`); `chokepoint_tension` (`chokepoint × date × index_value`); `reshoring_index` (`date × value`, aggregated from earnings-call transcripts).
- Universe: `universe_commodities.yaml` (futures CL/BZ/NG/HG + resource-country ETFs + frontier + semi-periphery). All marked `descriptive_only: true` until a commodity/EM factor model is added.
- Studies: `studies/sanctions_rerouting_fade.yaml`, `studies/reshoring_semi_periphery_returns.yaml`, `studies/frontier_resource_returns.yaml`.
- Ingest: `sanctions_ofac.yaml`, `sanctions_eu.yaml`, `chokepoint_eia.yaml`, `earnings_calls_reshoring.yaml`.

### Layer B — Marxian analytical add-ons

Three semantic label classes applied over Layer A events:

**B1 — Circuits of capital → sanctions rerouting.** When sanctions hit, commodities re-route through third countries (Russian crude → India refineries → EU as refined products). Most sanctions models assume flows stop; they don't. Label class: `sanctions_rerouting_stage ∈ {spike, rerouting_infrastructure_forming, normalized}`. Study: fade the initial spike once stage transitions to `rerouting_infrastructure_forming`.

**B2 — Luxemburg's ongoing primitive accumulation → resource frontiers.** New extraction frontiers open when accumulation exhausts existing ones (Guyana oil, DRC cobalt, Chile/Argentina/Australia lithium, African rare earths). Label class: `frontier_extraction_thesis` applied to `frontier_resources` universe group. Study: multi-year residual returns of frontier names vs benchmark commodity ETFs.

**B3 — World-systems / semi-periphery rise → near-shoring beneficiaries.** Wallerstein/Arrighi framework predicts which semi-periphery states catch the manufacturing shift (Vietnam, Mexico, Morocco, Poland, India). Label class: `semi_periphery_beneficiary_thesis` applied to `semi_periphery` universe group. Study: multi-year residual returns of semi-periphery ETFs vs SPY/EEM, conditioned on `reshoring_index` level.

**Kill risks (whole strategy).** Fat-tailed geopolitical events are idiosyncratic — edge is on *pricing* of chronic tension, not predicting events. Commodity/EM factor model absence forces `descriptive_only` posture initially. World-systems returns are multi-year — patience required.

**Execution home.** Sibling repo trades commodity futures via IBKR, long-dated options on frontier/semi-periphery ETFs.

---

## #6 — Policy dispersion (regime-shift detector)

**Premise.** Institutional prior lag. Think tanks, sell-side research, and financial press were trained on the 1980–2015 Washington Consensus (free trade, permissive antitrust, tax cuts). Since ∼2016 the regime is shifting — bipartisan protectionism, revived antitrust (Khan/Kanter), industrial policy (CHIPS, IRA). Dispersion across think-tank stances on a live policy question is a leading indicator of Overton-window motion, which prediction markets tend to under-price until the shift becomes obvious.

**Stratum surface.**

- Store: shares `articles` and `article_labels` tables. New `policy_stance_labels` table (grain: `article_id × policy_question_id × classifier_version`) with stance in `[−1, +1]`. New `prediction_market_prices` table (grain: `market_id × timestamp`) populated from scraped Kalshi + PredictIt archive.
- Universe: N/A per-instrument. A `policy_questions.yaml` config lists tracked questions.
- Study: `studies/policy_dispersion.yaml`.
- Ingest: `ingest/specs/think_tanks.yaml`, `ingest/specs/prediction_market_kalshi.yaml`, `ingest/specs/prediction_market_predictit_archive.yaml`.

**Signal.** For each policy question: LLM classifies each think-tank publication's stance in `[−1, +1]`. Rolling 90d `dispersion = variance(stance)`. Trend the dispersion. Signal fires when dispersion rising AND direction of shift diverges from current market price.

**Study.** Pre-registered classes: `dispersion_rising_toward_heterodox`, `dispersion_rising_toward_orthodox`, `dispersion_flat`. Hypothesis: prediction-market price movement over subsequent 30d is directionally predicted by class.

**Kill risks.** Small N of major policy events per year. Subjective LLM classification (mitigated by `classifier_version` pinning). Kalshi historical data quality varies by market; PredictIt archive is fixed.

**Execution home.** Sibling repo trades Kalshi/ForecastEx policy contracts (merger blocks, tariff sticking, bill passage).

---

## Analytical toolkit reference

- **Circuits of capital** (M–C–P–C′–M′): informational asymmetry in financial media (#1, #2), sanctions rerouting (#7B1).
- **Reserve army of labor**: wage/inflation-persistence regime (#3).
- **Falling rate of profit / overaccumulation**: crisis-cycle timing (#4).
- **Primitive accumulation (Luxemburg)**: resource-frontier identification (#7B2).
- **World-systems (Wallerstein, Arrighi)**: semi-periphery investment thesis (#7B3).
- **Kaleckian profit equation**: cross-check on #4 and sectoral read on #1.

Adjacent heterodox schools drawn on: Post-Keynesian, MMT (fiscal-dominance sensitivity), Minskyan financial-instability, Institutionalist (regime shift in #6).

## Explicitly dropped

- **Labor-action alpha (originally #5 in the scoping doc).** Kalshi strike-contract listings are sparse and illiquid; the equity-vol sample is too small to be systematic. Revisit only as an ad-hoc overlay if #1/#3 pipelines exist and specific strike events warrant it.
- **PRC state-signal decoder.** Xinhua/People's Daily are lagging propaganda outputs. No edge vs institutional China desks (Rhodium, Trivium, Gavekal), and they don't inform *global* trends anyway.
