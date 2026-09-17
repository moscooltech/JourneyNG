"""State machine transition tests (spec §9)."""

from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.models.journey import can_transition
from app.models.participant import participant_can_transition
from app.services.state_machines import require_journey_transition


class TestJourneyStateMachine:
    def test_draft_to_invited_allowed(self):
        assert can_transition("DRAFT", "INVITED")

    def test_invited_to_active_allowed(self):
        assert can_transition("INVITED", "ACTIVE")

    def test_invited_to_cancelled_allowed(self):
        assert can_transition("INVITED", "CANCELLED")

    def test_active_to_completed_allowed(self):
        assert can_transition("ACTIVE", "COMPLETED")

    def test_completed_cannot_reactivate(self):
        assert not can_transition("COMPLETED", "ACTIVE")

    def test_cancelled_cannot_reactivate(self):
        assert not can_transition("CANCELLED", "ACTIVE")

    def test_expired_cannot_reactivate(self):
        assert not can_transition("EXPIRED", "ACTIVE")

    def test_require_raises_on_invalid(self):
        with pytest.raises(AppError) as exc:
            require_journey_transition("COMPLETED", "ACTIVE")
        assert exc.value.code.value == "JOURNEY_INVALID_TRANSITION"


class TestParticipantStateMachine:
    def test_invited_to_accepted(self):
        assert participant_can_transition("INVITED", "ACCEPTED")

    def test_invited_to_declined(self):
        assert participant_can_transition("INVITED", "DECLINED")

    def test_accepted_to_active(self):
        assert participant_can_transition("ACCEPTED", "ACTIVE")

    def test_active_to_arrived(self):
        assert participant_can_transition("ACTIVE", "ARRIVED")

    def test_arrived_is_terminal(self):
        assert not participant_can_transition("ARRIVED", "ACTIVE")
        assert not participant_can_transition("ARRIVED", "LEFT")

    def test_declined_is_terminal(self):
        assert not participant_can_transition("DECLINED", "ACCEPTED")

    def test_left_is_terminal(self):
        assert not participant_can_transition("LEFT", "ACTIVE")

    def test_removed_is_terminal(self):
        assert not participant_can_transition("REMOVED", "ACTIVE")
