# The mlLm bridge

`semantic/mllm_bridge.py` types every stratum study's pre-registration as an
[mlLm](../../mlLm) `core.claim.Prediction`. This document is the mapping
table; the module docstring carries the epistemic argument for why this
exists and what it does and doesn't claim.

## Why

mlLm's own falsifiability contract (CLAUDE.md § Determinism Requirements)
schedules Phase 5 — Prediction Tracking — last, and "was this
historical-materialist analysis correct" rarely has a near-term, uncontested
ground truth. Stratum's studies do: an earnings print, an FOMC decision, a
Kalshi contract settle on ordinary timescales. Typing a study's hypothesis as
a `Prediction` means mlLm's confidence-ceiling and provenance machinery gets
real exercise years before any RAG/OCR pipeline could produce one.

See mlLm's `docs/architecture/INITIAL_AUDIT.md` § 5 for the other side of
this argument.

## The mapping

| Study | `framework:` | Basis |
|---|---|---|
| `reserve_army_regime_earnings_conditioning.yaml` | `orthodox-marxism` | Reserve army of labor is Marx's own concept (*Capital* Vol. I, ch. 25) |
| `overaccumulation_macro_regime.yaml` | `orthodox-marxism` | Falling-rate-of-profit / overaccumulation is Marx's crisis theory (*Capital* Vol. III) |
| `consensus_fade_fomc.yaml` | `orthodox-marxism` | Circuits of capital (M-C-P-C′-M′) is Marx's own schema (*Capital* Vol. II) |
| `class_sentiment_overlay.yaml` | `orthodox-marxism` | Same circuits-of-capital lens as `consensus_fade_fomc.yaml` |
| `sanctions_rerouting_fade.yaml` | `orthodox-marxism` | Circuits-of-capital lens applied to physical commodity flows |
| `frontier_resource_returns.yaml` | `luxemburgism` | Luxemburg's ongoing-primitive-accumulation thesis |
| `reshoring_semi_periphery_returns.yaml` | `world-systems-theory` | Wallerstein/Arrighi semi-periphery thesis |
| `policy_dispersion.yaml` | `institutionalism` | Institutional prior lag / Overton-window motion — see § Resolved gap below |

Every mapping to `orthodox-marxism` above is a direct attribution to Marx's
own concepts, not a default. Where `HETERODOX_STRATEGIES.md` notes overlap
with an adjacent, non-Marxist school (e.g. `overaccumulation_macro_regime`'s
overlap with the Kaleckian profit equation and Minskyan financial
instability), that overlap is cross-framework borrowing per META.md §
Framework Roster — Rules ("Citing an associated thinker outside the declared
framework is permissible only if the citation is acknowledged as
cross-framework borrowing") — acknowledged in the study's own YAML comment,
never folded silently into the declared `framework:`.

## Resolved gap: study #6 (`policy_dispersion`)

`policy_dispersion.yaml`'s mechanism — institutional prior lag / Overton-window
motion — is Institutionalist economics. As of mlLm v0.6 it had no slot in
either of mlLm's two rosters:

* **`core.framework.Framework`** (14 Marxist currents) — Institutionalism
  isn't a Marxist current.
* **`core.framework.AdversarialTradition`** (12 schools mlLm tests its own
  output *against*) — this roster exists to host schools mlLm reasons
  *about*, not schools it reasons *from*. Putting `policy_dispersion` here
  would misrepresent the study as an adversarial stress-test rather than a
  first-class hypothesis.

mlLm's `Tradition` type was `Literal["marxist"] | AdversarialTradition` — a
closed binary, with no third bucket for a friendly, non-Marxist heterodox
lens, even though `HETERODOX_STRATEGIES.md` § Analytical toolkit reference
explicitly draws on several (Post-Keynesian, MMT, Kaleckian, Minskyan,
Institutionalist) as adjacent schools stratum treats as real analytical
tools, not opposition.

**mlLm v0.7 closed this gap directly**, adding `core.framework.HeterodoxEconomicTradition`
(5 schools: Institutionalism, Post-Keynesianism, Kaleckian Economics, Modern
Monetary Theory, Minskyan Financial-Instability Theory) and
`AnalyticalLens = Framework | HeterodoxEconomicTradition` as the actual type
of every claim's `framework:` field — see mlLm's META.md § Heterodox-Economic
Tradition Roster. `policy_dispersion.yaml` now declares
`framework: institutionalism` and produces a valid `Prediction` like every
other study; `UnmappedFrameworkError` remains in the bridge as a guard for
whatever study comes next, not because this one still needs it (see
`tests/test_mllm_bridge.py::test_unmapped_framework_still_raises_on_a_constructed_payload`).

This also surfaced a real, separate bug that resolving the framework gap
made visible: `policy_dispersion.yaml`'s `window.post: 30` is *calendar*
days (it matches `response.horizon_days: 30` exactly), not the trading-day
sessions every other study's window uses per ARCHITECTURE.md's event-study
convention. Wiring #6 in without also fixing this would have silently
inflated its 30-day horizon to ~43 days under the trading-day approximation.
Every study now declares an explicit `window_unit` (`trading_days` or
`calendar_days`); the bridge requires it (`KeyError` if absent) rather than
defaulting, because a wrong default here is exactly the kind of error that
looks like it works.

## Epistemic status

Every `Prediction` this bridge produces reflects **design-time** state only:
zero confidence (pinned, not a placeholder — see the module docstring's
`_zero_confidence` note), and every citation `verifiable=False`, pointing at
the documented `data/raw/` contract rather than a fetched artifact. No study
has been run; Phase 0 (ingest) has no committed ingester yet. Recomputing a
real confidence value happens once `quant/event_study.py` actually executes
a study — this bridge does not, and should not, anticipate that result.
