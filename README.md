# stratum

A research engine that puts a **semantic layer** over **quantitative market data**, and tests whether the semantics hold up.

Two studies, one shared substrate:

**A. Event studies over a semantic timeline.** Build a dated, typed event log per instrument — earnings from broker data, plus product/regulatory/guidance events classified from text — then measure abnormal returns around each event *class*. The numbers say what happened; the semantic layer says what kind of thing it was.

**B. Semantic peer graph vs. realized correlation.** IBKR exposes a curated graph of competitors and investment themes with narrative evidence. Treat that graph as a *hypothesis* about relatedness and validate it against residual return correlation. Disagreements between the two are the output.

The joint study is the point: run an event study on a **semantically-defined cluster** rather than a single name, and measure earnings information transfer from a bellwether to its peers.

---

## Why this isn't just a screener

Every retail tool can compute an EPS surprise. None can answer *"does this name behave differently when it beats but guides down"* — that requires reading. And every tool can compute correlation, but correlation between two megacap semis is ~0.7 on market beta alone and tells you nothing. This repo does two things differently:

- **Semantic labels are treated as data**, with provenance — model, prompt version, timestamp, supporting evidence — so studies are reproducible and label sets are diffable when a prompt changes.
- **Correlation is always residual**, computed after regressing out the market factor, so the graph is tested against idiosyncratic co-movement rather than shared beta.

---

## Hard constraints (read before designing a study)

These are verified against the live MCP endpoints, not assumed.

**1. Earnings history is 8 quarters per ticker.** `get_earnings_results` returns the trailing eight, of which ~6 have actuals. Six events is not a sample. **Every study is pooled across names by design**; per-name output is descriptive history and is never presented as inference.

**2. Report timing is `am`/`pm` and it matters.** A `pm` report lands after the close, so `t=0` is the *next* session. Misaligning this silently halves the measured effect. Alignment is handled in one place (`quant/calendar.py`) and tested.

**3. The semantic graph has no history.** Theme and competitor edges are a point-in-time snapshot — the evidence text cites current financials, meaning themes are assigned with hindsight. Any study using the graph over past returns carries look-ahead bias *in the graph itself*, which no amount of careful return handling fixes. This is encoded as a required flag on every study config, not a comment in a docstring.

  > Use B for current risk description and hypothesis generation. Do not use it to claim a historical edge.

**4. Python cannot reach the MCP servers.** They are bound to the Claude session, not to the shell. So the agent is the ingestion runtime: it executes fetch specs and writes raw JSON to `data/raw/`, and Python reads only from there. See `ARCHITECTURE.md` — this boundary is deliberate, makes the compute layer deterministic and offline-testable, and is what keeps the project usable by people without broker MCP access (see *Portability* below).

**5. Contract resolution is noisy.** `search_contracts("NVDA")` returns 22 rows, mostly leveraged and income ETFs (NVDL, NVDY, NVDU…). Resolution requires exact symbol match plus `country_code: US` plus primary listing, or the peer graph quietly fills with derivatives of the thing you meant.

---

## What gets built, in order

| Phase | Deliverable | Depends on |
|---|---|---|
| 0 | Ingest + store + universe resolution | — |
| 1 | **Theme concentration report** — position dollars mapped through the theme graph | 0 |
| 2 | Residual correlation matrix + the 2×2 (Study B) | 1 |
| 3 | Earnings event study, pooled (Study A, numeric classes only) | 0 |
| 4 | Semantic event classification + non-earnings timeline | 3 |
| 5 | Cluster information-transfer study (A × B) | 2, 4 |

Phase 1 is deliberately first: it is a single pass over the graph, read-only, and it either tells you something surprising about your actual concentration in the first ten minutes or it doesn't.

---

## Portability

The reference ingester uses Claude with Robinhood and IBKR MCP servers, which almost nobody else has. That would normally make the repo unrunnable by anyone but its author — except that the compute layer never talks to a broker. It reads `data/raw/**` and nothing else.

So **the raw layout is a public contract, not an implementation detail.** Any ingester that writes the documented JSON shapes drives the entire pipeline unchanged:

```
data/raw/<source>/<endpoint>/<key>.json      # response, verbatim
data/raw/<source>/<endpoint>/<key>.meta.json # provenance sidecar
```

`ARCHITECTURE.md` specifies the required shapes. A yfinance- or CSV-backed ingester is a legitimate contribution and needs to touch nothing under `quant/` or `semantic/`. If you write one, the studies should reproduce.

---

## Safety posture

- **Read-only.** No order-placement tool is called from this repo, ever. Not behind a flag, not in a dry-run mode. The MCP servers expose `place_equity_order` and friends; nothing here touches them, and a PR adding a write path will be declined.
- **`data/` is gitignored in full**, and `.githooks/pre-commit` hard-blocks any staged path under it. Enable with `git config core.hooksPath .githooks` after cloning. This repo is public; your positions are not.
- No credentials or account numbers in the repo. They are supplied at runtime.

---

## License

**AGPL-3.0.** Copyleft, deliberately: run a modified version as a network service and you owe your users the source. The intent is that improvements to the research machinery stay available to everyone using it.

## Disclaimer

Research tooling, not investment advice. It is explicitly built to make it *harder* to fool yourself — pre-registered event classes, look-ahead blocking, underpowered samples reported as underpowered — and it will still happily produce a confident-looking chart from a bad hypothesis. Nothing here recommends buying or selling anything. The tickers in `UNIVERSE.md` are a test bench chosen for statistical properties, not merit.

---

## Status

Scaffolding. Nothing computes yet. See `ARCHITECTURE.md` for the design and `UNIVERSE.md` for the starting instrument set.
