"""Tests for 7-stage coordination pipeline engine — S12-03."""
import pytest

from app.coordination.pipeline_engine import (
    PIPELINE_STAGES,
    InvalidTransitionError,
    record_stage_timestamp,
    validate_transition,
)


class TestPipelineStages:
    def test_is_tuple(self):
        assert isinstance(PIPELINE_STAGES, tuple)

    def test_has_eight_stages(self):
        assert len(PIPELINE_STAGES) == 8

    def test_event_is_first(self):
        assert PIPELINE_STAGES[0] == "Event"

    def test_close_is_last(self):
        assert PIPELINE_STAGES[-1] == "Close"

    def test_contains_acknowledge(self):
        assert "Acknowledge" in PIPELINE_STAGES

    def test_contains_execute(self):
        assert "Execute" in PIPELINE_STAGES

    def test_contains_verify(self):
        assert "Verify" in PIPELINE_STAGES

    def test_contains_notify(self):
        assert "Notify" in PIPELINE_STAGES


class TestValidateTransitionValid:
    def test_open_to_acknowledged(self):
        validate_transition("OPEN", "ACKNOWLEDGED")

    def test_acknowledged_to_executing(self):
        validate_transition("ACKNOWLEDGED", "EXECUTING")

    def test_executing_to_verified(self):
        validate_transition("EXECUTING", "VERIFIED")

    def test_verified_to_closed(self):
        validate_transition("VERIFIED", "CLOSED")


class TestValidateTransitionInvalid:
    def test_open_to_closed_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("OPEN", "CLOSED")

    def test_open_to_executing_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("OPEN", "EXECUTING")

    def test_open_to_verified_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("OPEN", "VERIFIED")

    def test_acknowledged_to_open_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("ACKNOWLEDGED", "OPEN")

    def test_acknowledged_to_closed_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("ACKNOWLEDGED", "CLOSED")

    def test_closed_to_anything_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("CLOSED", "OPEN")

    def test_unknown_from_status_raises(self):
        with pytest.raises(InvalidTransitionError, match="Unknown from_status"):
            validate_transition("BOGUS", "ACKNOWLEDGED")

    def test_unknown_to_status_raises(self):
        with pytest.raises(InvalidTransitionError, match="Unknown to_status"):
            validate_transition("OPEN", "BOGUS")

    def test_error_message_contains_statuses(self):
        with pytest.raises(InvalidTransitionError, match="OPEN"):
            validate_transition("OPEN", "CLOSED")

    def test_same_status_raises(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("OPEN", "OPEN")


class TestRecordStageTimestamp:
    def test_returns_dict(self):
        result = record_stage_timestamp(None, "ACKNOWLEDGED", "2026-08-04T10:00:00Z")
        assert isinstance(result, dict)

    def test_status_key_stored(self):
        result = record_stage_timestamp(None, "ACKNOWLEDGED", "2026-08-04T10:00:00Z")
        assert "ACKNOWLEDGED" in result

    def test_timestamp_value_stored(self):
        result = record_stage_timestamp(None, "ACKNOWLEDGED", "2026-08-04T10:00:00Z")
        assert result["ACKNOWLEDGED"] == "2026-08-04T10:00:00Z"

    def test_existing_entries_preserved(self):
        existing = {"OPEN": "2026-08-04T09:00:00Z"}
        result = record_stage_timestamp(existing, "ACKNOWLEDGED", "2026-08-04T10:00:00Z")
        assert result["OPEN"] == "2026-08-04T09:00:00Z"
        assert "ACKNOWLEDGED" in result

    def test_none_input_gives_single_entry(self):
        result = record_stage_timestamp(None, "EXECUTING", "2026-08-04T11:00:00Z")
        assert len(result) == 1

    def test_input_dict_not_mutated(self):
        existing = {"OPEN": "T0"}
        record_stage_timestamp(existing, "ACKNOWLEDGED", "T1")
        assert "ACKNOWLEDGED" not in existing
