"""Every real study config round-trips through the mllm bridge.

This is the demonstration, not a synthetic example: all 8 studies
committed under studies/ are loaded exactly as event_study.py will one
day load them, and each is asserted to produce either a valid
core.claim.Prediction or the specific, named UnmappedFrameworkError.
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

# Every study file that must produce a valid Prediction.
MAPPED_STUDIES = [f for f in STUDY_FILES if f.name != "policy_dispersion.yaml"]

FIXED_AS_OF = datetime(2026, 9, 13, tzinfo=UTC)


def test_all_eight_study_files_are_discovered():
    """Guards against a silent glob/rename mismatch hiding a study."""
    assert len(STUDY_FILES) == 8
    assert len(MAPPED_STUDIES) == 7


@pytest.mark.parametrize("path", MAPPED_STUDIES, ids=lambda p: p.stem)
def test_mapped_study_produces_a_valid_prediction(path):
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


@pytest.mark.parametrize("path", MAPPED_STUDIES, ids=lambda p: p.stem)
def test_prediction_round_trips_through_json(path):
    """The Prediction produced is a real, persistable record."""
    study = load_study(path)
    original = study_to_prediction(study, as_of=FIXED_AS_OF)
    reloaded = Prediction.model_validate_json(original.model_dump_json())
    assert reloaded == original


def test_policy_dispersion_raises_the_named_error_not_a_bad_mapping():
    """study #6's lens (institutional prior lag) has no Framework slot.

    The bridge must refuse, loudly and specifically, rather than default
    to some framework and misrepresent the study's actual lens.
    """
    study = load_study(STUDIES_DIR / "policy_dispersion.yaml")
    assert study["framework"] is None
    with pytest.raises(UnmappedFrameworkError, match="policy_dispersion"):
        study_to_prediction(study, as_of=FIXED_AS_OF)


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
    }
    with pytest.raises(KeyError):
        study_to_prediction(incomplete, as_of=FIXED_AS_OF)
