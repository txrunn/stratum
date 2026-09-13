# Theory

Grounding document for the heterodox analytical toolkit used across `HETERODOX_STRATEGIES.md`. This is not the operational doc — that one describes signal mechanics, store tables, and study configs. This one answers a narrower question: **for each analytical claim a study makes, what is the actual theoretical source, and what falsifiable prediction does it license?**

## Posture

Marxian and adjacent heterodox economics are used here as an **analytical toolkit**, in the Dengist sense — whichever framework predicts the data, use it. Three explicit disclaimers:

1. **No labor-theory-of-value price calculations.** Nothing here computes socially-necessary-labor-time or derives prices from embodied labor. The toolkit borrowed is the *institutional and dynamic* analysis (class position, accumulation cycles, crisis tendencies, core-periphery structure) — not the value-theoretic price system, which is a separate and much more contested part of the corpus.
2. **No endorsement of any political program.** Citing Marx, Luxemburg, Lenin, Wallerstein, or Gramsci here is citation of an analytical claim, exactly as citing Friedman or Fama would be. The studies are agnostic about what should happen; they test what a given theory predicts will happen.
3. **Heterodox theory is a source of hypotheses, not ground truth.** Every claim below is operationalized as a pre-registered study (see `HETERODOX_STRATEGIES.md` and `studies/*.yaml`) that can fail. A theory that doesn't survive the event-study test is dropped, same as any other hypothesis. Two entries below already were (see "Rejected or downgraded" at the end).

---

## Anchors, by study

### #1 — Consensus fade on macro releases

**Not** circuits of capital (that framework is about capital's sequence of forms — money capital → productive capital → commodity capital → money capital — and doesn't map cleanly onto "which sources get quoted in financial media"). Correct anchors:

- **Herman & Chomsky, *Manufacturing Consent* (1988)** — the propaganda model's five filters (ownership, advertising, sourcing, flak, ideology) predict *whose voice appears in coverage*, which is the actual mechanism behind #1's claim that financial media oversamples money-capital's viewpoint. The filter that does the work here is **sourcing**: business-desk journalism relies heavily on official/corporate sources because they're cheap, reliable, and repeat-business — not because of any conspiracy.
- **Bourdieu, *On Television* (1996)** and *the sociology of journalistic fields* — journalists within a field compete for position using the same limited set of legitimate sources and framings, which produces exactly the kind of high sentiment-uniformity #1's signal is built to detect. Uniformity is predicted by field dynamics, not by the "correctness" of the uniform view.
- **Schudson**, *The Sociology of News* — complementary account of how news production routines (not individual bias) generate systematic coverage patterns.

**Falsifiable claim:** coverage skewed toward official/money-capital sources under-samples productive-capital and household-balance-sheet signals, and that under-sampling correlates with directional mispricing around the event. `consensus_fade_fomc.yaml` tests this directly.

### #2 — Class-position-weighted sentiment

Same anchors as #1 (Herman-Chomsky, Bourdieu), applied to the *comparison* between capital-press and labor-press coverage rather than to capital-press alone. The added claim: labor-press outlets sit in a different position in Herman-Chomsky's ownership/advertising filters (non-profit, subscriber- or union-funded, no advertiser dependency on the subjects covered), so their coverage samples a materially different information set. The sentiment gap is a proxy for that difference in filter structure.

**Falsifiable claim:** `sentiment_gap` (capital − labor) predicts a directional correction not captured by capital-press sentiment alone. `class_sentiment_overlay.yaml`.

### #3 — Reserve army of labor

- **Marx, *Capital* Vol. 1, Ch. 25** ("The General Law of Capitalist Accumulation") — the reserve army of labor (unemployed and underemployed workers) functions as a wage-discipline mechanism. When the reserve is large, labor's bargaining power is weak; when it's thin, wages and labor share of income rise. This is the direct analytical ancestor of NAIRU / Phillips-curve reasoning in mainstream macro — the same empirical claim, different vocabulary and different causal story (institutional bargaining power vs. a mechanical inflation-expectations trade-off).
- **Kalecki, "Political Aspects of Full Employment" (1943)** — the sharper, testable companion. Kalecki predicted that sustained full employment (a thin reserve army) creates political and business pressure to engineer a downturn specifically *because* it erodes capital's disciplinary power over labor, independent of any inflation argument. This gives #3 a second, distinct prediction beyond wage/margin pressure: business-cycle policy responses may correlate with reserve-army tightness net of inflation readings.

**Falsifiable claim:** post-earnings SCAR differs by reserve-army regime because margin/labor-cost sensitivity is regime-dependent. `reserve_army_regime_earnings_conditioning.yaml`.

### #4 — Overaccumulation / falling rate of profit

- **Marx, *Capital* Vol. 3, Ch. 13–15** — the tendency of the rate of profit to fall as capital intensity rises, and the countervailing tendencies (cheapening of constant capital, super-exploitation, foreign trade, etc.) that can offset it for periods. The "regime" framing in #4 is explicitly about periods where the countervailing tendencies are exhausted, not a claim that profit rates fall monotonically.
- **Kalecki's profit equation** — `P = I + Cₖ − Sw + G + NX` (aggregate profits equal investment plus capitalist consumption minus worker saving plus government deficit plus net exports). This is the actual testable macro identity behind #4's financialization-ratio signal: when investment (I) is displaced by buybacks/dividends (which enter through Cₖ, capitalist consumption, not I), the profit-generating engine of the economy weakens by identity, not by assumption. This is arguably the single most rigorous piece of the whole toolkit — it's an accounting identity, not a theory that could be "wrong" in the way a behavioral claim could be.
- **Harvey, *Limits to Capital* (1982)** — the "spatial fix" and "temporal fix": capital facing overaccumulation in one location/time period seeks new outlets (new markets, new geographies, longer-duration investment like infrastructure) rather than simply crashing. Relevant complement to #4 for understanding *where* displaced capital goes rather than just *that* margins compress.
- **Minsky, "Financial Instability Hypothesis" (1986)** — non-Marxian but directly complementary: stability breeds increasing risk-taking (hedge → speculative → Ponzi financing), which is functionally similar to #4's financialization-ratio claim (capital increasingly used for financial engineering rather than productive investment) even though the causal mechanism (endogenous risk appetite vs. class-distributional struggle) differs. Using both as cross-checks is intentional — if only one framework's signal fires, that's useful information about which mechanism is actually in play.

**Falsifiable claim:** forward 6m/12m SPY returns are lower conditional on the high-financialization/falling-profit regime. `overaccumulation_macro_regime.yaml`.

### #6 — Policy dispersion

**Not** primarily a Marxian claim, despite living in the heterodox-strategies doc. The actual mechanism:

- **Kuhn, *The Structure of Scientific Revolutions* (1962)** — paradigm lag: an interpretive community (here, think tanks and financial press) continues operating within an existing paradigm even as anomalies accumulate, until a period of crisis produces a genuine paradigm shift. #6's claim that "institutions trained on the 1980–2015 Washington Consensus lag in recognizing a policy regime shift" is a Kuhnian claim about interpretive communities, not a Marxian one about class position.
- **Gramsci, *Prison Notebooks*** — hegemony: a dominant ideological framework doesn't collapse all at once; it loses coherence gradually as counter-hegemonic positions gain institutional footing (new think tanks, new coalitions) before the shift becomes visible in mainstream discourse. This is the mechanism behind treating *dispersion* (not just mean stance) as the leading indicator — a hegemonic shift shows up first as increased contestation, before the new position wins.

**Falsifiable claim:** rising 90-day dispersion in think-tank stance predicts subsequent prediction-market price movement. `policy_dispersion.yaml`.

### #7 — Commodity + imperialism

- **Lenin, *Imperialism, the Highest Stage of Capitalism* (1917)** and **Bukharin, *Imperialism and World Economy* (1917)** — imperialism as an economic category: capital export, the fusion of financial and industrial capital, and the territorial competition among capitalist states for markets and raw materials, as opposed to a purely political/military reading of great-power competition. This underwrites #7A's premise that chokepoint tension and sanctions activity are *economically structural*, not episodic — they recur because inter-state competition over resource access is a persistent feature of the system, not a one-off crisis.
- **World-systems theory (Wallerstein, Arrighi)** — core-periphery-semiperiphery structure predicts *which* commodity flows and *which* countries are contested (see #7B3 below).

### #7B1 — Circuits of capital → sanctions rerouting

**This is the one place "circuits of capital" is the correct anchor**, unlike its misapplication in #1. Marx, *Capital* Vol. 2 — capital's circuit runs M → C → P → C′ → M′ (money capital buys commodities, which are transformed by production into new commodities, which are sold for more money). The circuit describes the physical/logistical path a commodity actually takes through production and exchange, which is exactly the right lens for "when a sanction blocks one circuit, capital finds another" (Russian crude → India refining → EU as refined product is a rerouted circuit, not a blocked one). Complementary: **Harvey's spatial fix** again — rerouting is a spatial fix at the level of a single commodity flow.

**Falsifiable claim:** the initial sanctions-driven price spike fades once a new circuit (rerouting infrastructure) forms. `sanctions_rerouting_fade.yaml`.

### #7B2 — Primitive accumulation → resource frontiers

- **Luxemburg, *The Accumulation of Capital* (1913)** — capitalism requires a continuously expanding "outside" (non-capitalist economies, unexploited resources) to absorb surplus and provide cheap inputs; when one frontier is exhausted, capital moves to the next. This is a stronger and more specific claim than generic "commodity supercycle" reasoning: it predicts *structural, recurring* frontier-opening as a feature of accumulation, not a random walk of discovery.
- **Harvey, *The New Imperialism* (2003)** — "accumulation by dispossession," the modern extension of Luxemburg's argument: land/resource enclosure, privatization of commons, and debt-driven asset transfer as ongoing (not merely historical, pre-capitalist) processes.

**Falsifiable claim:** frontier-extraction-thesis-labeled names show persistent multi-year residual returns vs. a broad commodity peer basket. `frontier_resource_returns.yaml` (descriptive-only pending a commodity factor model).

### #7B3 — World-systems → semi-periphery manufacturing

- **Wallerstein, *The Modern World-System* (1974–2011, multi-volume)** — core/semi-periphery/periphery as a structural, not merely descriptive, hierarchy: semi-periphery states perform a specific functional role (absorbing manufacturing that core states shed) and mobility between tiers is a real but constrained process.
- **Arrighi, *The Long Twentieth Century* (1994)** — systemic cycles of accumulation: hegemonic transitions (Genoese → Dutch → British → American) are accompanied by manufacturing capacity relocating to a rising semi-peripheral power. The current US-China relationship and the "China+1" reshoring pattern is read here as a live instance of exactly this dynamic, with Vietnam/Mexico/India/Poland as candidate beneficiaries of the next relocation.

**Falsifiable claim:** semi-periphery ETF residual returns are conditioned on the reshoring_index level, consistent with a systemic relocation already underway. `reshoring_semi_periphery_returns.yaml` (descriptive-only pending an EM equity factor model).

---

## Adjacent (non-Marxian) heterodox schools referenced

- **Post-Keynesian** — endogenous money, fundamental uncertainty. Background framework for treating financial cycles as internally generated rather than externally shocked; relevant to #4.
- **MMT (Modern Monetary Theory)** — fiscal-dominance sensitivity. Relevant to how #4's macro regime interacts with government deficit spending in the Kaleckian profit identity (the `+ G` term).
- **Minskyan financial-instability hypothesis** — see #4 above.
- **Institutionalist economics** (Veblen, Commons, and modern successors) — background for #6's treatment of think tanks and policy institutions as path-dependent actors rather than neutral forecasters.

---

## Rejected or downgraded

Keeping this section because a toolkit that never rejects anything isn't being used analytically — it's decoration.

- **PRC state-signal decoding** (originally proposed as part of #7). Rejected: Xinhua/People's Daily are lagging propaganda outputs, telegraphing decisions already made rather than predicting anything. No edge over institutional China desks (Rhodium, Trivium, Gavekal) who already parse these documents professionally. See `HETERODOX_STRATEGIES.md` "Explicitly dropped."
- **Labor-action alpha via strike-contract prediction markets** (originally #5). Rejected: Kalshi strike-contract listings are too sparse and illiquid to be a systematic signal, not because the underlying labor-action-as-signal idea is theoretically wrong.
- **"Circuits of capital" as the anchor for #1** (see above) — corrected, not rejected outright. The mistake was applying a physical-commodity-flow framework to a media-coverage question. Replaced with Herman-Chomsky/Bourdieu, which is the actually-applicable literature for that claim.
