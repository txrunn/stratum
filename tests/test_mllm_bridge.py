"""Every real study config round-trips through the mllm bridge.

This is the demonstration, not a synthetic example: all 8 studies
committed under studies/ are loaded exactly as event_study.py will one
day load them, and each is asserted to produce a valid
core.claim.Prediction. (UnmappedFrameworkError and the window_unit
requirement are exercised against constructed payloads below — no
committed study currently triggers either, which is itself the point:
policy_dispersion was the one gap, and mlLm v0.7's
HeterodoxEconomicTradition roster closed it.)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from core.claim import Prediction
from pydantic import ValidationError

from stratum.semantic.mllm_bridge import (
    UnmappedFrameworkError,
    load_study,
    study_to_prediction,
)

STUDIES_DIR = Path(__file__).parent.parent / "studies"
STUDY_FILES = sorted(STUDIES_DIR.glob("*.yaml"))

FIXED_AS_OF = datetime(2026, 9, 13, tzinfo=UTC)


def test_all_eight_study_files_are_discovered():
    """Guards against a silent glob/rename mismatch hiding a study."""
    assert len(STUDY_FILES) == 8


@pytest.mark.parametrize("path", STUDY_FILES, ids=lambda p: p.stem)
def test_every_committed_study_produces_a_valid_prediction(path):
    study = load_study(path)
    prediction = study_to_prediction(study, as_of=FIXED_AS_OF)

    assert isinstance(prediction, Prediction)
    assert prediction.claim_id == f"stratum-study:{study['name']}"
    assert prediction.framework == study["framework"]
    assert prediction.confidence.overall_confidence == 0.0
    assert len(prediction.citations) >= 1
    assert prediction.citations[0].verifiable is False
    assert prediction.target_date > FIXED_AS_OF
    assert prediction.time_horizon > timedelta(0)


@pytest.mark.parametrize("path", STUDY_FILES, ids=lambda p: p.stem)
def test_prediction_round_trips_through_json(path):
    """The Prediction produced is a real, persistable record."""
    study = load_study(path)
    original = study_to_prediction(study, as_of=FIXED_AS_OF)
    reloaded = Prediction.model_validate_json(original.model_dump_json())
    assert reloaded == original


def test_policy_dispersion_maps_to_institutionalism():
    """The resolved gap: study #6's lens now has a real home.

    mlLm v0.7 added HeterodoxEconomicTradition specifically for this
    case (see META.md § Heterodox-Economic Tradition Roster and
    docs/mllm_bridge.md § Resolved gap).
    """
    study = load_study(STUDIES_DIR / "policy_dispersion.yaml")
    assert study["framework"] == "institutionalism"
    prediction = study_to_prediction(study, as_of=FIXED_AS_OF)
    assert prediction.framework == "institutionalism"


def test_policy_dispersion_horizon_uses_calendar_days_not_trading_days():
    """The unit bug this bridge would have shipped if #6 had been wired
    in without also fixing window_unit: window.post=30 is calendar days
    (it matches response.horizon_days=30 exactly). Applying the
    trading-day approximation would inflate it to ~43 days."""
    study = load_study(STUDIES_DIR / "policy_dispersion.yaml")
    assert study["window_unit"] == "calendar_days"
    prediction = study_to_prediction(study, as_of=FIXED_AS_OF)
    assert prediction.target_date == FIXED_AS_OF + timedelta(days=30)


def test_event_study_horizon_uses_trading_day_approximation():
    """Contrast case: an event-study-style config's window.post is
    trading-day sessions, not calendar days, and should NOT come out to
    exactly that many calendar days."""
    study = load_study(STUDIES_DIR / "consensus_fade_fomc.yaml")
    assert study["window_unit"] == "trading_days"
    prediction = study_to_prediction(study, as_of=FIXED_AS_OF)
    # post=3 trading days -> slightly more than 3 calendar days.
    assert prediction.target_date > FIXED_AS_OF + timedelta(days=3)
    assert prediction.target_date < FIXED_AS_OF + timedelta(days=5)


def test_unmapped_framework_still_raises_on_a_constructed_payload():
    """No committed study exercises this path anymore; the guard itself
    must still work for whatever study is added next."""
    incomplete = {
        "name": "hypothetical_unmapped_study",
        "framework": None,
        "hypothesis": "placeholder",
        "classes": ["a", "b"],
        "min_events_per_class": 5,
        "window_unit": "trading_days",
    }
    with pytest.raises(UnmappedFrameworkError, match="hypothetical_unmapped_study"):
        study_to_prediction(incomplete, as_of=FIXED_AS_OF)


def test_falsification_criteria_reference_the_studys_own_classes():
    """Falsification text must come from the study's registered classes,
    never invented prose — this is the pre-registration discipline."""
    study = load_study(STUDIES_DIR / "reserve_army_regime_earnings_conditioning.yaml")
    prediction = study_to_prediction(study, as_of=FIXED_AS_OF)
    (criterion,) = prediction.falsification_criteria
    for registered_class in study["classes"]:
        assert registered_class in criterion


def test_confidence_ceiling_forbids_hand_raising_pre_run_confidence():
    """A pre-registered, not-yet-run study cannot claim nonzero confidence —
    enforced by ConfidenceAssessment itself, not by this bridge's discipline."""
    from core.claim import ConfidenceAssessment

    with pytest.raises(ValidationError, match="must not exceed"):
        ConfidenceAssessment(
            evidence_quality=0.0,
            source_reliability=0.0,
            framework_consistency=0.0,
            uncertainty_penalty=0.0,
            overall_confidence=0.1,
            rationale="Attempting to overstate a pre-run study's confidence.",
        )


def test_missing_hypothesis_field_fails_loudly():
    """A study wired through this bridge without the new mandatory fields
    must fail with a clear KeyError, not silently produce a hollow claim."""
    incomplete = {
        "name": "no_hypothesis_study",
        "framework": "orthodox-marxism",
        "classes": ["a", "b"],
        "min_events_per_class": 5,
        "window_unit": "trading_days",
    }
    with pytest.raises(KeyError):
        study_to_prediction(incomplete, as_of=FIXED_AS_OF)


def test_missing_window_unit_fails_loudly_rather_than_guessing():
    """window_unit has no default on purpose — see the module docstring's
    policy_dispersion example for what a wrong guess would silently do."""
    incomplete = {
        "name": "no_window_unit_study",
        "framework": "orthodox-marxism",
        "hypothesis": "placeholder",
        "classes": ["a", "b"],
        "min_events_per_class": 5,
        "window": {"post": 30},
    }
    with pytest.raises(KeyError):
        study_to_prediction(incomplete, as_of=FIXED_AS_OF)


def test_invalid_window_unit_is_rejected():
    payload = {
        "name": "bad_window_unit_study",
        "framework": "orthodox-marxism",
        "hypothesis": "placeholder",
        "classes": ["a", "b"],
        "min_events_per_class": 5,
        "window_unit": "fortnights",
        "window": {"post": 2},
    }
    with pytest.raises(ValueError, match="window_unit must be one of"):
        study_to_prediction(payload, as_of=FIXED_AS_OF)
