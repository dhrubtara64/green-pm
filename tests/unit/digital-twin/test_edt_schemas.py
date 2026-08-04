"""Tests for Executive Digital Twin + Command Centre schemas — S17-02, S17-03, S17-04."""
import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.twin.schemas import (
    COMMAND_CENTRE_PANEL_COUNT,
    COMMAND_CENTRE_PANELS,
    EDT_PANELS,
    CommandCentrePanelCreate,
    CommandCentrePanelResponse,
    CommandCentreUpdate,
    EDTSynthesisCreate,
    EDTSynthesisResponse,
    EDTSynthesisSpec,
)


class TestEDTPanels:
    def test_has_three_panels(self):
        assert len(EDT_PANELS) == 3

    def test_reality_present(self):
        assert "REALITY" in EDT_PANELS

    def test_forecast_present(self):
        assert "FORECAST" in EDT_PANELS

    def test_required_decisions_present(self):
        assert "REQUIRED_DECISIONS" in EDT_PANELS

    def test_is_frozenset(self):
        assert isinstance(EDT_PANELS, frozenset)


class TestCommandCentrePanels:
    def test_has_eight_panels(self):
        assert len(COMMAND_CENTRE_PANELS) == 8

    def test_count_constant_is_eight(self):
        assert COMMAND_CENTRE_PANEL_COUNT == 8

    def test_risks_present(self):
        assert "RISKS" in COMMAND_CENTRE_PANELS

    def test_dependencies_present(self):
        assert "DEPENDENCIES" in COMMAND_CENTRE_PANELS

    def test_vendors_present(self):
        assert "VENDORS" in COMMAND_CENTRE_PANELS

    def test_readiness_present(self):
        assert "READINESS" in COMMAND_CENTRE_PANELS

    def test_forecasts_present(self):
        assert "FORECASTS" in COMMAND_CENTRE_PANELS

    def test_decisions_present(self):
        assert "DECISIONS" in COMMAND_CENTRE_PANELS

    def test_alignment_present(self):
        assert "ALIGNMENT" in COMMAND_CENTRE_PANELS

    def test_simulations_present(self):
        assert "SIMULATIONS" in COMMAND_CENTRE_PANELS

    def test_is_frozenset(self):
        assert isinstance(COMMAND_CENTRE_PANELS, frozenset)

    def test_no_overlap_with_edt_panels(self):
        assert len(EDT_PANELS & COMMAND_CENTRE_PANELS) == 0


class TestEDTSynthesisSpec:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            synthesis_date=date(2026, 8, 4),
            panels={"REALITY": {"risks": 3}, "FORECAST": {}, "REQUIRED_DECISIONS": {}},
        )
        defaults.update(kwargs)
        return EDTSynthesisSpec(**defaults)

    def test_creates_successfully(self):
        spec = self._make()
        assert isinstance(spec.project_id, uuid.UUID)

    def test_is_frozen(self):
        spec = self._make()
        with pytest.raises((AttributeError, TypeError)):
            spec.synthesis_date = date(2026, 1, 1)  # type: ignore[misc]

    def test_panels_stored(self):
        panels = {"REALITY": {"a": 1}, "FORECAST": {}, "REQUIRED_DECISIONS": {}}
        spec = self._make(panels=panels)
        assert spec.panels == panels

    def test_synthesis_date_stored(self):
        d = date(2026, 8, 11)
        spec = self._make(synthesis_date=d)
        assert spec.synthesis_date == d

    def test_empty_panels_raises(self):
        with pytest.raises(ValueError):
            self._make(panels={})

    def test_invalid_panel_name_raises(self):
        with pytest.raises(ValueError, match="Invalid EDT panel"):
            self._make(panels={"INVALID_PANEL": {}})

    def test_valid_partial_panels_accepted(self):
        spec = self._make(panels={"REALITY": {}})
        assert "REALITY" in spec.panels

    def test_all_three_panels_valid(self):
        spec = self._make(panels={p: {} for p in EDT_PANELS})
        assert len(spec.panels) == 3


class TestCommandCentreUpdate:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            panel_name="RISKS",
            panel_data={"count": 5},
            triggered_by_event="risk.updated",
        )
        defaults.update(kwargs)
        return CommandCentreUpdate(**defaults)

    def test_creates_successfully(self):
        upd = self._make()
        assert upd.panel_name == "RISKS"

    def test_is_frozen(self):
        upd = self._make()
        with pytest.raises((AttributeError, TypeError)):
            upd.panel_name = "VENDORS"  # type: ignore[misc]

    def test_triggered_by_event_stored(self):
        upd = self._make(triggered_by_event="readiness.gate.passed")
        assert upd.triggered_by_event == "readiness.gate.passed"

    def test_triggered_by_event_none_accepted(self):
        upd = self._make(triggered_by_event=None)
        assert upd.triggered_by_event is None

    def test_invalid_panel_raises(self):
        with pytest.raises(ValueError, match="Invalid Command Centre panel"):
            self._make(panel_name="NONEXISTENT")

    def test_all_cc_panels_valid(self):
        for panel in COMMAND_CENTRE_PANELS:
            upd = self._make(panel_name=panel)
            assert upd.panel_name == panel


class TestEDTSynthesisCreate:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            synthesis_date=date(2026, 8, 4),
        )
        defaults.update(kwargs)
        return EDTSynthesisCreate(**defaults)

    def test_creates_successfully(self):
        create = self._make()
        assert isinstance(create.project_id, uuid.UUID)

    def test_reality_panel_defaults_empty(self):
        create = self._make()
        assert create.reality_panel == {}

    def test_forecast_panel_defaults_empty(self):
        create = self._make()
        assert create.forecast_panel == {}

    def test_decisions_panel_defaults_empty(self):
        create = self._make()
        assert create.decisions_panel == {}

    def test_synthesis_date_stored(self):
        d = date(2026, 8, 11)
        create = self._make(synthesis_date=d)
        assert create.synthesis_date == d

    def test_panels_accepted(self):
        create = self._make(
            reality_panel={"risk_count": 3},
            forecast_panel={"completion": "2026-12"},
            decisions_panel={"pending": 2},
        )
        assert create.reality_panel["risk_count"] == 3


class TestEDTSynthesisResponse:
    def test_creates_from_dict(self):
        resp = EDTSynthesisResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            synthesis_date=date(2026, 8, 4),
        )
        assert resp.reality_panel == {}

    def test_synthesized_at_defaults_none(self):
        resp = EDTSynthesisResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            synthesis_date=date(2026, 8, 4),
        )
        assert resp.synthesized_at is None

    def test_from_attributes_config(self):
        assert EDTSynthesisResponse.model_config.get("from_attributes") is True


class TestCommandCentrePanelCreate:
    def _make(self, **kwargs):
        defaults = dict(
            project_id=uuid.uuid4(),
            panel_name="RISKS",
        )
        defaults.update(kwargs)
        return CommandCentrePanelCreate(**defaults)

    def test_creates_successfully(self):
        create = self._make()
        assert create.panel_name == "RISKS"

    def test_panel_data_defaults_empty(self):
        create = self._make()
        assert create.panel_data == {}

    def test_triggered_by_event_defaults_none(self):
        create = self._make()
        assert create.triggered_by_event is None

    def test_invalid_panel_name_raises(self):
        with pytest.raises(ValidationError):
            self._make(panel_name="GHOST_PANEL")

    def test_all_cc_panels_accepted(self):
        for panel in COMMAND_CENTRE_PANELS:
            create = self._make(panel_name=panel)
            assert create.panel_name == panel

    def test_panel_data_accepted(self):
        create = self._make(panel_data={"count": 7})
        assert create.panel_data["count"] == 7


class TestCommandCentrePanelResponse:
    def test_creates_from_dict(self):
        resp = CommandCentrePanelResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            panel_name="RISKS",
        )
        assert resp.panel_data == {}

    def test_updated_at_defaults_none(self):
        resp = CommandCentrePanelResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            panel_name="VENDORS",
        )
        assert resp.updated_at is None

    def test_triggered_by_event_defaults_none(self):
        resp = CommandCentrePanelResponse(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            panel_name="DECISIONS",
        )
        assert resp.triggered_by_event is None

    def test_from_attributes_config(self):
        assert CommandCentrePanelResponse.model_config.get("from_attributes") is True
