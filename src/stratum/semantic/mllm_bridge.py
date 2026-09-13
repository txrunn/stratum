"""Types a stratum study's pre-registration as an mlLm ``core.claim.Prediction``.

mlLm (sibling repo, colocated during development) defines a falsifiability
contract — CLAUDE.md § Determinism Requirements, § Provenance Requirements —
that historical-materialist analysis has struggled to exercise: "was this
analysis correct" rarely has a near-term, uncontested ground truth. Stratum's
studies do: an earnings print, an FOMC decision, a Kalshi contract all settle
on ordinary timescales. mlLm's own README.md schedules Phase 5 (Prediction
Tracking) last, which risks it never arriving; this module makes stratum the
Phase 5 vehicle instead of waiting for one to be built from scratch. See
mlLm's ``docs/architecture/INITIAL_AUDIT.md`` § 5.

``study_to_prediction`` builds the ``Prediction`` **mechanically** from a
study YAML's own registered fields — ``hypothesis``, ``classes``,
``min_events_per_class``, ``robustness``, ``allow_lookahead`` — never from
prose an LLM or this bridge invents. That mirrors ARCHITECTURE.md's own
design principle ("a study is a file, not a function call") and CLAUDE.md's
"prefer computation over generation": the falsification criteria a study can
be judged against must themselves be pre-registered, not synthesized after
the fact by whatever is doing the typing.

Epistemic status of the object this produces: a ``Prediction`` built here
reflects **design-time** state only. No stratum study has been run — Phase 0
(ingest) has no committed ingester and `data/raw/` is empty by construction
(gitignored; see stratum's README.md § Safety posture). Accordingly:

* ``confidence`` is pinned at zero across every component. This is not a
  placeholder to be raised later by hand — it is the correct value for a
  claim with no evidence collected yet, and the rationale field says so.
* Every ``Citation`` is ``verifiable=False`` and points at the *documented
  raw-layout contract* the study will read from (``ARCHITECTURE.md``'s
  ``data/raw/<source>/<endpoint>/<key>.json``), not at a resolved artifact.
  Nothing has been fetched, so nothing can yet be machine-verified against
  a fetched artifact.
* ``target_date`` is derived from the study's ``window.post`` under a
  trading-day approximation (252 sessions/year) because stratum's own
  session-accurate calendar (``quant/calendar.py``) is unimplemented
  (ARCHITECTURE.md lists it as owning "the single place the am/pm rule
  lives"). Once it exists, replace ``_approximate_trading_days`` here with a
  real call into it and this module's own test suite will need updating —
  the approximation is deliberately isolated to one function for that reason.

None of this is deception dressed as rigor: the point of putting a
not-yet-run study through mlLm's schema at all is that CLAUDE.md's
Provenance/Confidence machinery gets to say, structurally, "this is a
registered hypothesis, not yet evidence" — which is exactly the distinction
EPISTEMOLOGY.md's confidence-ceiling rule exists to make impossible to
overstate by construction.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.claim import ConfidenceAssessment, Prediction
from core.provenance import Citation, LocatorType, SourceLocator, SourceType

# Sessions per year, used only to convert a study's window.post (trading
# days) into an approximate calendar target_date. See module docstring.
_TRADING_DAYS_PER_YEAR = 252
_CALENDAR_DAYS_PER_TRADING_DAY = 365.25 / _TRADING_DAYS_PER_YEAR


class UnmappedFrameworkError(ValueError):
    """Raised when a study declares ``framework: null``.

    This is a finding, not a bug to route around: the study's analytical
    lens has no slot in mlLm's core.framework.Framework roster (14 Marxist
    currents) or its AdversarialTradition roster (schools mlLm tests
    itself against, not schools it reasons from). See the ``framework:``
    comment in the affected study's YAML for the specific gap, and mlLm's
    Tradition type (``Literal["marxist"] | AdversarialTradition``), which
    has no third bucket for a friendly non-Marxist heterodox lens.
    """


def _approximate_trading_days(days: int) -> timedelta:
    """Convert a count of trading-day sessions to an approximate timedelta.

    See module docstring — isolated here so it is the one place to change
    when stratum's quant/calendar.py exists and can do this exactly.
    """
    return timedelta(days=days * _CALENDAR_DAYS_PER_TRADING_DAY)


def _zero_confidence(rationale: str) -> ConfidenceAssessment:
    """The correct ConfidenceAssessment for a claim with no evidence yet.

    ceiling = min(evidence_quality, source_reliability) - uncertainty_penalty
            = min(0.0, 0.0) - 0.0 = 0.0, so overall_confidence must be 0.0.
    This is enforced by ConfidenceAssessment itself, not asserted here.
    """
    return ConfidenceAssessment(
        evidence_quality=0.0,
        source_reliability=0.0,
        framework_consistency=0.0,
        uncertainty_penalty=0.0,
        overall_confidence=0.0,
        rationale=rationale,
    )


def _ingest_contract_citation(citation_id: str, source_name: str) -> Citation:
    """A citation to a documented-but-unfetched raw-data contract.

    Per ARCHITECTURE.md, `data/raw/<source>/<endpoint>/<key>.json` is a
    public contract independent of which ingester writes it. Pointing a
    Citation at the contract itself (verifiable=False) records *what
    evidence this study is designed to consume* without claiming any of
    it has actually been fetched or checked.
    """
    return Citation(
        citation_id=citation_id,
        source_id=f"stratum:data/raw/{source_name}",
        source_type=SourceType.DATASET,
        locator=SourceLocator(kind=LocatorType.NONE, value="not yet fetched"),
        retrieval_chunk_id=None,
        verifiable=False,
    )


def study_to_prediction(
    study: dict[str, Any],
    *,
    as_of: datetime | None = None,
) -> Prediction:
    """Build a core.claim.Prediction from a loaded stratum study config.

    Args:
        study: A study YAML loaded with ``yaml.safe_load`` (e.g. via
            ``load_study``). Must carry the ``framework`` and
            ``hypothesis`` fields added alongside this bridge.
        as_of: The registration timestamp the prediction's time_horizon is
            measured from. Defaults to now (UTC). Pass a fixed value in
            tests for a reproducible ``target_date``.

    Raises:
        UnmappedFrameworkError: if ``study["framework"]`` is ``None``
            (currently true only of ``policy_dispersion.yaml`` — see its
            own ``framework:`` comment).
        KeyError: if the study is missing ``hypothesis``, ``classes``, or
            ``min_events_per_class`` — all mandatory once a study is
            wired through this bridge.
    """
    framework = study.get("framework")
    if framework is None:
        raise UnmappedFrameworkError(
            f"{study['name']!r} declares framework: null — its analytical "
            "lens has no mlLm Framework/AdversarialTradition mapping. See "
            "the study YAML's own framework: comment for the specific gap."
        )

    name: str = study["name"]
    hypothesis: str = " ".join(study["hypothesis"].split())  # collapse YAML block-scalar whitespace
    classes: list[str] = study["classes"]
    min_events: int = study["min_events_per_class"]
    descriptive_only: bool = bool(study.get("descriptive_only", False))
    window = study.get("window") or {}
    post_days = int(window.get("post", 0)) if window else 0

    as_of = as_of or datetime.now(UTC)
    horizon = _approximate_trading_days(max(post_days, 1))

    evaluation_method = (
        "Descriptive report only; no pooled t-statistic (study is "
        "descriptive_only)."
        if descriptive_only
        else (
            "quant/event_study.py pooled mean SCAR, cross-sectional "
            f"t-statistic, bootstrap CI; class reports as underpowered "
            f"below min_events_per_class={min_events} rather than "
            "producing a p-value."
        )
    )

    robustness_assumptions = tuple(
        f"Robustness variant registered: {entry}"
        for entry in study.get("robustness", [])
    ) or ("No robustness variants registered for this study.",)

    return Prediction(
        claim_id=f"stratum-study:{name}",
        statement=hypothesis,
        framework=framework,
        confidence=_zero_confidence(
            "Pre-registration only; no ingestion has run, no computation "
            f"exists for {name!r} yet (stratum Phase 0 is unimplemented). "
            "Recompute from event_study.py's bootstrap CI once the study "
            "actually executes; do not raise this by hand."
        ),
        citations=(
            _ingest_contract_citation(f"{name}-ingest-contract", "<see study events_source>"),
        ),
        time_horizon=horizon,
        target_date=as_of + horizon,
        falsification_criteria=(
            (
                f"Pooled result over registered classes {classes!r} shows no "
                f"meaningful difference between them beyond sampling noise, "
                f"at min_events_per_class={min_events}."
            ),
        ),
        assumptions=robustness_assumptions,
        expected_outcomes=(
            (
                f"At least one registered class in {classes!r} shows a pooled "
                "effect distinguishable from the others, subject to the "
                f"min_events_per_class={min_events} floor."
            ),
        ),
        evaluation_criteria=(evaluation_method,),
    )


def load_study(path: Path) -> dict[str, Any]:
    """Load one study YAML. Thin wrapper so callers don't import yaml directly."""
    import yaml

    return yaml.safe_load(path.read_text())
