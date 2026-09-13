# Architecture

## The governing constraint: the agent is the ingestion runtime

The MCP servers (Robinhood, IBKR, Google Calendar) are bound to the Claude session. A standalone Python process cannot call them. Rather than fight this, the boundary is made explicit and load-bearing:

```
┌─────────────────────────────────────────────────────────┐
│  CLAUDE SESSION  (the only thing that touches network)  │
│                                                          │
│   reads  ingest/specs/*.yaml   →   calls MCP tools       │
│                                →   writes data/raw/**    │
└─────────────────────────────────────────────────────────┘
                             │
                    data/raw/ (JSON, append-only)
                             │
┌─────────────────────────────────────────────────────────┐
│  PYTHON  (pure, offline, deterministic, testable)       │
│                                                          │
│   raw → normalize → SQLite → compute → report            │
└─────────────────────────────────────────────────────────┘
```

**Why this is good rather than merely necessary:**

- The compute layer has no network dependency, so tests run offline against fixtures and studies are reproducible from a raw snapshot.
- Raw JSON is append-only and content-addressed, so re-running a study a month later reproduces the original result exactly rather than silently picking up revised data.
- Rate limiting and retry live entirely in the agent, not scattered through the analysis code.
- A scheduled cloud agent can perform ingestion on a cron without any of the compute layer changing.

A fetch spec declares *what* to retrieve, never *how*:

```yaml
# ingest/specs/earnings.yaml
source: robinhood
endpoint: get_earnings_results
fanout: {over: universe.all, as: symbol}
cache: {key: "{symbol}", ttl_days: 7}
```

The agent expands the fanout, calls the tool, and writes each response verbatim to
`data/raw/robinhood/get_earnings_results/{symbol}.json` alongside a sidecar recording
fetch timestamp, tool version, and parameters.

The same spec pattern extends to non-MCP sources. `source: fred_alfred`, `source: rss`, `source: http_json`, and `source: scrape` are all first-class — the agent's ingester dispatches by `source` name, writes to `data/raw/<source>/<endpoint>/...`, and the compute layer never cares which one produced a given raw file. See `HETERODOX_STRATEGIES.md` for the ingest specs used by the news, macro, sanctions, and prediction-market pipelines.

---

## Layers

```
src/stratum/
├── ingest/      spec parsing, raw→normalized adapters, provenance sidecars
├── store/       SQLite schema, loaders, point-in-time query helpers
├── semantic/    event classification, graph construction, label store
├── quant/       calendar, returns, market model, event study, correlation
└── report/      CLI tables + Artifact HTML generation
```

### `store/` — two clocks, always

Every row carries both:

- **`event_time`** — when the thing happened in the world
- **`knowledge_time`** — when we could first have known it

Point-in-time queries filter on `knowledge_time <= as_of`. This is what makes a look-ahead-free study *mechanically* possible rather than a matter of discipline. Where a source cannot supply a real `knowledge_time` — the theme graph being the main offender — it gets the snapshot date and the row is flagged `pit_unsafe = true`. Any study that touches a `pit_unsafe` row must set `allow_lookahead: true` in its config or the run aborts.

Core tables:

| Table | Grain | Notes |
|---|---|---|
| `instruments` | one per resolved security | RH symbol ↔ IBKR `contract_id` ↔ ISIN; resolution evidence retained |
| `bars` | symbol × date | daily OHLCV, `adjustment_type` recorded per row |
| `earnings` | symbol × fiscal quarter | estimate, actual, report date, `am/pm`, `verified` |
| `events` | instrument × event_time | typed timeline; earnings and non-earnings unified |
| `themes` | one per theme key | name, description |
| `theme_membership` | theme × instrument | includes `rank` (1 = most central) |
| `competitor_edges` | instrument → instrument | directed, `rank`, evidence text |
| `labels` | event × classifier_version | semantic outputs, with provenance |
| `positions` | account × symbol × snapshot | gitignored, never committed |
| `runs` | one per study execution | config hash, input snapshot hash, results |

SQLite is the right call here: single user, single writer, no concurrency, and the entire database is a file you can copy to pin a snapshot.

### Additional tables for heterodox studies

See `HETERODOX_STRATEGIES.md` for the full study designs. These extend the core schema without changing it; the two-clock discipline applies to every row.

| Table | Grain | Notes |
|---|---|---|
| `macro_series` | `series_id × observation_date × vintage_date` | FRED/ALFRED. `knowledge_time = vintage_date` (ALFRED `realtime_start`). Vintage-aware; latest-only queries filter on `MAX(vintage_date) OVER (series_id, observation_date) WHERE vintage_date <= as_of`. |
| `articles` | `article_id` | `source`, `title`, `url`, `published_at`, `knowledge_time` (fetch time), `body_hash`, `outlet_class ∈ {capital, labor, mixed, think_tank}`. |
| `article_labels` | `article_id × classifier_version` | `sentiment [-1,+1]`, `confidence [0,1]`, `circuit ∈ {money, productive, consumption, mixed}`, evidence span, model id, prompt hash. |
| `policy_stance_labels` | `article_id × policy_question_id × classifier_version` | Stance in `[-1, +1]`; used by #6. Kept separate from `article_labels` because a single article can hold stances on multiple questions. |
| `sanctions_events` | `id` | `event_time`, `source_agency ∈ {ofac, eu, uk}`, `target_entity`, `target_commodity`, `action`, `url`. |
| `chokepoint_tension` | `chokepoint × date` | Composite index from news mentions + shipping-rate deviation. Provenance stored per-observation. |
| `labor_activity_series` | `metric × period_start × region` | NLRB election petitions and ULP charges — counts, not text. `knowledge_time` = NLRB release date, not `period_end` (reporting lag is several weeks; using `period_end` would leak). Quantitative complement to `article_labels`-derived labor-press sentiment (#2) and an independent input alongside FRED aggregates in the #3 reserve-army composite. |
| `reshoring_index` | `date` | Aggregate frequency of reshoring/friend-shoring/nearshoring/China+1 language in earnings-call transcripts. |
| `prediction_market_prices` | `market_id × timestamp` | `yes_price`, `no_price`, `volume`, `source ∈ {kalshi, predictit_archive, forecastex}`. PredictIt archive rows are historical-only; Kalshi rows carry live provenance. |

The `events.type` enumeration is extended: `earnings`, `macro_release` (subtype: `fomc`/`cpi`/`nfp`/`gdp`/`pce`), `sanctions_action`, `policy_milestone`. New event types slot into pooled studies via the same event-study harness.

### `semantic/` — labels are versioned data

Classification is nondeterministic and costs money, so nothing is classified twice and nothing is classified anonymously. Each label row records the classifier version, prompt hash, model id, timestamp, the extracted evidence span, and a self-reported confidence.

Consequences that matter:

- Changing a prompt does not invalidate history — it creates a new `classifier_version`, and old and new label sets can be **diffed** to see exactly which events changed class and whether a study's conclusion survives.
- A study pins a `classifier_version`. Re-running reproduces.
- Low-confidence labels can be excluded as a robustness check rather than silently trusted.

Heterodox studies introduce three additional classifier families (`article_sentiment`, `policy_stance`, `sanctions_rerouting_stage`), each versioned independently and pinned per study.

### `quant/` — pure functions over the store

No network, no LLM calls, no I/O beyond the database. Every function here is unit-testable against fixtures.

**`calendar.py`** owns event alignment, and is the single place the `am`/`pm` rule lives:

```
report at 2026-02-25, timing = pm   →   t=0 is 2026-02-26 (next session)
report at 2026-02-25, timing = am   →   t=0 is 2026-02-25
```

Also owns trading-day arithmetic, so `t-5` means five *sessions* back, not five calendar days. Macro-release events use the same alignment: a `pm` FOMC statement lands after the close, so `t=0` is the next session.

**`market_model.py`** — estimation window `[-250, -30]` trading days, ending strictly before the event so the fit cannot see the outcome:

```
r_it   = α_i + β_i·r_mt + ε_it
AR_it  = r_it − (α̂_i + β̂_i·r_mt)
CAR_i  = Σ AR_it   over the event window
SCAR_i = CAR_i / (σ̂_εi · √n)      standardized by estimation-window residual vol
```

Standardizing is not optional — without it a single volatile name dominates any pooled mean.

Non-equity instruments (commodity futures, EM ETFs) are excluded from pooled inference until a commodity factor model and an EM-equity factor model exist. They enter `bars`/`events` with `descriptive_only: true` and every study touching them either pins the flag or drops them.

**`event_study.py`** — pools events by class, reports mean SCAR with a cross-sectional t-statistic and a bootstrap confidence interval. Enforces three hygiene rules:

1. **Overlap guard** — events whose windows intersect another event on the same instrument are flagged and excluded by default.
2. **Minimum N** — a class below the configured floor reports as underpowered rather than producing a p-value.
3. **Pre-registration** — event classes are declared in the study config *before* the run. Classes added after seeing results are recorded as exploratory and reported separately.

That third rule exists because with ~170 events and a dozen candidate classes you will find significance by accident.

**`correlation.py`** — residual correlation, never raw:

```
r_it = α_i + β_i·r_mt + ε_it        (market factor removed; SPY)
ρ_ij = corr(ε_i, ε_j)
```

Computed over multiple windows (60d, 250d) to expose stability, and separately over down-market days only — the standard finding is that diversification evaporates precisely when it's needed, and this makes that checkable for a specific portfolio.

Semantic similarity, for comparison against `ρ_ij`:

```
s_ij = w₁·(1/competitor_rank_ij) + w₂·Σ_shared_themes  1/√(rank_i · rank_j)
```

Theme co-membership at high rank on both sides is the stronger term. Competitor rank is noisier because the edge conflates rivalry with partnership — IBKR lists Alphabet as NVDA's rank-4 competitor while it is simultaneously a major customer. That ambiguity is a feature: it is exactly the kind of edge the correlation test should adjudicate.

### `report/`

CLI tables for iteration; Artifact HTML for anything worth keeping. Every report embeds the run's config hash and input snapshot hash so a chart can always be traced to the data that produced it.

---

## Study configs

A study is a file, not a function call. This is what makes pre-registration enforceable.

```yaml
# studies/earnings_surprise_pooled.yaml
name: earnings_surprise_pooled
universe: universe.core_ai + universe.hyperscalers
benchmark: SPY
window: {pre: -1, post: 5}
estimation: {start: -250, end: -30}
classes:                      # pre-registered, before any results are seen
  - beat_and_rose
  - beat_and_fell             # the interesting quadrant
  - miss_and_rose
  - miss_and_fell
min_events_per_class: 20
allow_lookahead: false
classifier_version: null      # numeric classes only — no semantic labels used
```

The `runs` table stores the config hash next to the results, so an exploratory variant can never be mistaken for the pre-registered one.

Heterodox studies use additional config fields:

- `conditioning_variables:` — list of `macro_series`-derived regime flags to partition the event class on (e.g., `reserve_army_regime`, `overaccumulation_regime`).
- `classifier_version:` gains real values (e.g., `article_sentiment@v3`) when semantic labels are consumed. Pinning is mandatory.
- `descriptive_only:` — explicit flag to run without pooled inference, used for #7 commodity/EM studies until factor models exist.

---

## Open questions

- **Historical option data depth.** `get_option_historicals` exists; if it reaches back far enough to reconstruct the pre-earnings straddle at past report dates, the implied-vs-realized move study becomes possible. Needs probing before it goes on the roadmap.
- **ADR contamination.** TSM and ARM returns include an FX component that the market model will attribute to alpha. Either add a dollar-index factor or exclude them from pooled inference and keep them descriptive.
- **Theme graph expansion cost.** Traversal is combinatorial — 26 names × ~6 competitors × ~6 themes, with each theme holding 20–50 members. Phase 1 caps at one hop and top-20 theme rank; whether a second hop adds signal is an empirical question, not a design one.
- **Benchmark choice.** SPY for the market factor is the honest default, but a semis-heavy universe may want SMH as a second factor. Adding it risks regressing away the very co-movement Study B is trying to measure, so it stays a robustness check rather than the base specification.
- **Commodity/EM factor model.** #7 studies start `descriptive_only`. Candidates: DBC / GSG / DBA for commodity factors, EEM for EM equity factor. Which combination cleanly absorbs geopolitical premium without eating the very signal is an open empirical question.
- **Prediction-market historical data.** #6 depends on `prediction_market_prices`. Kalshi's public API covers current markets; PredictIt data has a fixed archive published after shutdown. Neither is a stable long-run source — the scrape spec pins a snapshot per run.
- **News-source licensing.** Capital-press RSS feeds are typically headline-only; full-body access requires paid feeds. Sentiment on headline-only text is coarser but not useless; the study configs record which mode was used.
