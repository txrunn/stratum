# Starting universe

26 instruments plus 4 benchmarks. Not a portfolio and not a recommendation list — a **test bench**, chosen so that both studies have something to find and something to fail against.

## Selection criteria

The universe has to satisfy the studies, not the other way around:

1. **Cluster density** — at least 4–5 names per theme, or the information-transfer study has no cross-section to average over.
2. **Reporting-order dispersion within a cluster** — a bellwether that reports early and peers that report later. Without staggered dates there is no transfer to measure, only contemporaneous correlation.
3. **A real control group** — names with genuinely low semantic connection to the core. If low-semantic pairs *don't* show low residual correlation, Study B's premise is wrong, and that has to be falsifiable.
4. **A cross-sector cluster** — names the theme graph links to AI infrastructure but GICS puts in Utilities and Industrials. This is the direct test of whether the semantic graph beats sector labels.
5. **Liquid options** — needed later for the implied-vs-realized move work.
6. **Deliberately ambiguous edges** — GOOGL is both NVDA's rank-4 competitor and one of its largest customers. Keep those; they're the cases where the correlation test earns its keep.

---

## Cluster 1 — Core AI / accelerated compute (10)

The dense core. IBKR's competitor graph for NVDA returns AMD, INTC, AVGO, GOOGL, QCOM, ARM at ranks 1–6, so these edges are already confirmed to exist in the data.

| Ticker | Role | Notes |
|---|---|---|
| NVDA | Cluster anchor | Reports late in season (Feb/May/Aug/Nov); fiscal year offset — FY2027 Q2 = Aug 2026 |
| AMD | Rank-1 competitor | Cleanest head-to-head edge in the graph |
| AVGO | Rank-3 competitor | **Off-cycle** (Dec/Mar/Jun/Sep) — decouples its events from the calendar-quarter crowd |
| INTC | Rank-2 competitor | High idiosyncratic vol; useful stress test for standardization |
| MU | Memory supply chain | **Off-cycle** (Sep/Dec/Mar/Jun); strong candidate bellwether |
| TSM | Foundry, upstream of everyone | **Earliest reporter** each season → primary bellwether. ADR: FX contamination, see flags |
| ARM | Rank-6 competitor, also licensor | ADR; supplier-competitor ambiguity is intentional |
| QCOM | Rank-5 competitor | Edge case — mostly edge/mobile, weaker datacenter link |
| MRVL | Custom silicon / networking | Tests whether the graph ranks it near AVGO |
| AMAT | Semicap equipment | Deeper upstream; should show a *lagged* rather than contemporaneous relationship |

**Bellwether chain:** TSM (earliest) → MU → NVDA → AVGO (latest). Four staggered anchors per cycle is the backbone of the information-transfer study.

## Cluster 2 — Hyperscalers / demand side (5)

Not competitors — **customers**. Capex guidance from these names is a directional, upstream signal into Cluster 1, which makes it a different kind of semantic edge from rivalry and a sharper test.

| Ticker | Notes |
|---|---|
| MSFT | Capex guidance is the highest-signal line item in the universe |
| GOOGL | Appears as an NVDA *competitor* (TPUs) while being a major customer — the ambiguous edge |
| AMZN | AWS capex; also owns Trainium silicon |
| META | Pure demand, no competing silicon of consequence |
| ORCL | **Off-cycle** (Jun/Sep/Dec/Mar); OCI backlog is a distinct signal |

## Cluster 3 — Power & datacenter physical layer (5)

The cross-sector test. The theme graph should connect these to AI infrastructure; GICS files them under Utilities and Industrials. If residual correlation with Cluster 1 is high while sector labels say "diversified," that is the **hidden-factor** cell of the 2×2 and the most valuable single result in Study B.

| Ticker | Sector per GICS | Actual exposure |
|---|---|---|
| VRT | Industrials | Datacenter cooling and power distribution |
| ETN | Industrials | Electrical infrastructure |
| GEV | Industrials | Grid and generation equipment |
| CEG | Utilities | Nuclear PPAs signed directly with hyperscalers |
| PWR | Industrials | Grid construction |

## Cluster 4 — Control (6)

Chosen for *low expected semantic connection* to Clusters 1–3, spanning several distinct factor exposures so the null isn't a single sector's story.

| Ticker | Factor |
|---|---|
| KO, PG | Staples / defensive |
| JNJ | Healthcare |
| WM | Industrials, domestic, low tech beta |
| JPM | Financials, rate-sensitive |
| XOM | Energy, commodity-driven |

These exist to be *unsurprising*. If the pipeline reports strong residual correlation between XOM and NVDA, the bug is in the pipeline.

## Benchmarks (4)

| Ticker | Use |
|---|---|
| SPY | Market factor in the base specification — the one that matters |
| QQQ | Robustness check |
| SMH | Semis factor. **Robustness only, never the base spec** — regressing it out would remove the exact co-movement Study B exists to measure |
| XLU | Utilities factor, for the Cluster 3 cross-sector claim |

---

## Fetch shape

30 symbols total. `get_equity_historicals` accepts up to 10 per call → **3 calls** for the full daily panel. `get_earnings_results` is one symbol per call → 26 calls, cached 7 days. IBKR graph calls need `contract_id` resolution first (26 `search_contracts` calls, cached indefinitely — contract IDs are stable).

## Flags to carry through the pipeline

- **`adr: true`** on TSM and ARM. Returns include an FX component the market model will misattribute to alpha. Keep them descriptive, or exclude from pooled inference, until a dollar factor is added.
- **`off_cycle: true`** on AVGO, MU, ORCL. A feature, not a problem — they spread the event calendar and reduce window overlap.
- **`fiscal_offset`** on NVDA. Fiscal labels do not match calendar quarters; always join on `report.date`, never on `year`/`quarter`.
- **`recent_ipo`** on GEV (2024 spinoff) and ARM (2023). Short history truncates the 250-day estimation window; verify before including in pooled runs.

## What's missing on purpose

**Your actual positions.** The universe above is a bench for validating the machinery. Phase 1 — the theme-concentration report — should run on the union of this bench and real holdings pulled from both brokers, because the interesting number is *your* concentration, not the bench's. Adding it needs account numbers supplied at runtime; they don't go in the repo.

Also absent: small caps (unreliable earnings verification), anything under ~$5B (option liquidity), and crypto-adjacent names (a distinct factor that would need its own cluster to be handled honestly rather than as noise).
