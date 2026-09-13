"""Reserve-army-of-labor composite. See HETERODOX_STRATEGIES.md #3, THEORY.md.

Marx's reserve army of labor: unemployed/underemployed workers function as a
wage-discipline mechanism on those in work. A thin reserve army means weak
disciplinary pressure — workers can bid wages up and resist speed-ups; a
thick one means the opposite. The composite below is a single number meant
to summarize "how thin is the reserve army right now," built entirely from
point-in-time FRED/ALFRED data (see store/pit.py) so it never uses a
revision that wasn't published yet as of the date being scored.

Component signs (documented here because "higher is tighter" is not
obvious for every series in isolation):

  U6RATE        higher = MORE slack (broader un/underemployment) -> inverted
  LNS11300060   higher = fewer people have dropped out of the labor force
                entirely (less *hidden*, uncounted reserve army) -> upright
  JTSQUR        higher quits = workers confident they can walk into a
                better job -> upright. Widely regarded as the best
                real-time tightness read of the five.
  ECIWAG        higher wage growth = labor capturing more bargaining
                power -> upright
  OPHNFB        productivity growth *in isolation*, i.e. not netted against
                wage growth here, is coded as capital capturing the gains
                (the empirically well-documented post-1980s productivity-pay
                gap) -> inverted. This is the weakest-founded of the five
                signs and carries the smallest weight for exactly that
                reason. A wage/productivity *gap* term (ECIWAG growth minus
                OPHNFB growth) would be a more defensible v2 formulation;
                not done here to keep v1's five independent terms matching
                what's already documented in HETERODOX_STRATEGIES.md and
                fred_series_alfred.yaml.

Weights sum to 1.0 and are a judgment call, not fit to data — fitting them
to historical outcomes before ever running the study would be the exact
look-ahead the pre-registration discipline exists to prevent.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from stratum.store.pit import macro_series_asof

COMPOSITE_VERSION = "reserve_army_composite@v1"

ROLLING_WINDOW_YEARS = 10
MIN_OBSERVATIONS = 12  # below this, a z-score is noise, not signal


@dataclass(frozen=True)
class Component:
    series_id: str
    weight: float
    higher_is_tighter: bool


COMPONENTS: tuple[Component, ...] = (
    Component("U6RATE", weight=0.25, higher_is_tighter=False),
    Component("LNS11300060", weight=0.15, higher_is_tighter=True),
    Component("JTSQUR", weight=0.30, higher_is_tighter=True),
    Component("ECIWAG", weight=0.20, higher_is_tighter=True),
    Component("OPHNFB", weight=0.10, higher_is_tighter=False),
)

assert abs(sum(c.weight for c in COMPONENTS) - 1.0) < 1e-9, "component weights must sum to 1.0"


@dataclass(frozen=True)
class CompositeResult:
    as_of: str
    value: float
    component_z_scores: dict[str, float]
    version: str = COMPOSITE_VERSION


def _lookback_start(as_of: str) -> str:
    d = date.fromisoformat(as_of)
    return date(d.year - ROLLING_WINDOW_YEARS, d.month, d.day).isoformat()


def _z_score(latest: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    if stdev == 0:
        return 0.0
    return (latest - mean) / stdev


def compute_composite(conn, as_of: str) -> CompositeResult | None:
    """The reserve-army composite as of `as_of`, using only PIT-safe data.

    Returns None if any component has fewer than MIN_OBSERVATIONS points in
    its trailing 10-year window as of `as_of` — reports "can't compute yet"
    rather than a number built on too little history to mean anything.
    """
    lookback_start = _lookback_start(as_of)
    z_scores: dict[str, float] = {}

    for component in COMPONENTS:
        obs = macro_series_asof(
            conn, component.series_id, as_of=as_of, lookback_start=lookback_start
        )
        values = [o.value for o in obs if o.value is not None]
        if len(values) < MIN_OBSERVATIONS:
            return None

        latest = values[-1]
        history = values[:-1]  # z-score against everything strictly before latest
        z = _z_score(latest, history) if history else 0.0
        if not component.higher_is_tighter:
            z = -z
        z_scores[component.series_id] = z

    composite_value = sum(c.weight * z_scores[c.series_id] for c in COMPONENTS)
    return CompositeResult(as_of=as_of, value=composite_value, component_z_scores=z_scores)
