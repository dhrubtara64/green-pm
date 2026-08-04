"""Tests for Green PM Studio schemas — S18-01."""
import uuid

import pytest

from app.studio.schemas import (
    BUILDER_COUNT,
    BUILDER_TYPES,
    BuilderConfig,
    BuilderCreate,
    BuilderResponse,
    target_engine_for,
)


class TestBuilderTypes:
    def test_exactly_fifteen_types(self):
        assert len(BUILDER_TYPES) == BUILDER_COUNT

    def test_builder_count_constant(self):
        assert BUILDER_COUNT == 15

    def test_wbs_template_present(self):
        assert "WBS_TEMPLATE" in BUILDER_TYPES

    def test_activity_template_present(self):
        assert "ACTIVITY_TEMPLATE" in BUILDER_TYPES

    def test_evidence_scoring_present(self):
        assert "EVIDENCE_SCORING" in BUILDER_TYPES

    def test_vendor_scorecard_present(self):
        assert "VENDOR_SCORECARD" in BUILDER_TYPES

    def test_risk_matrix_present(self):
        assert "RISK_MATRIX" in BUILDER_TYPES

    def test_dispatch_template_present(self):
        assert "DISPATCH_TEMPLATE" in BUILDER_TYPES

    def test_change_category_present(self):
        assert "CHANGE_CATEGORY" in BUILDER_TYPES

    def test_readiness_gate_present(self):
        assert "READINESS_GATE" in BUILDER_TYPES

    def test_simulation_scenario_present(self):
        assert "SIMULATION_SCENARIO" in BUILDER_TYPES

    def test_coordination_template_present(self):
        assert "COORDINATION_TEMPLATE" in BUILDER_TYPES

    def test_memory_pattern_present(self):
        assert "MEMORY_PATTERN" in BUILDER_TYPES

    def test_forecast_model_present(self):
        assert "FORECAST_MODEL" in BUILDER_TYPES

    def test_alignment_profile_present(self):
        assert "ALIGNMENT_PROFILE" in BUILDER_TYPES

    def test_decision_matrix_present(self):
        assert "DECISION_MATRIX" in BUILDER_TYPES

    def test_sync_policy_present(self):
        assert "SYNC_POLICY" in BUILDER_TYPES

    def test_types_is_frozenset(self):
        assert isinstance(BUILDER_TYPES, frozenset)


class TestBuilderConfig:
    def test_valid_construction(self):
        cfg = BuilderConfig(
            builder_type="WBS_TEMPLATE",
            name="My WBS",
            config_data={"levels": 3},
        )
        assert cfg.builder_type == "WBS_TEMPLATE"

    def test_name_stored(self):
        cfg = BuilderConfig("RISK_MATRIX", "Risk Config", {})
        assert cfg.name == "Risk Config"

    def test_config_data_stored(self):
        cfg = BuilderConfig("EVIDENCE_SCORING", "Scoring", {"weight": 0.5})
        assert cfg.config_data == {"weight": 0.5}

    def test_invalid_builder_type_raises(self):
        with pytest.raises(ValueError, match="Unknown builder_type"):
            BuilderConfig("INVALID_TYPE", "Name", {})

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            BuilderConfig("WBS_TEMPLATE", "", {})

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            BuilderConfig("WBS_TEMPLATE", "   ", {})

    def test_is_frozen(self):
        cfg = BuilderConfig("WBS_TEMPLATE", "My WBS", {})
        with pytest.raises(Exception):
            cfg.name = "changed"

    def test_target_engine_wbs(self):
        cfg = BuilderConfig("WBS_TEMPLATE", "WBS", {})
        assert cfg.target_engine == "core-platform"

    def test_target_engine_evidence_scoring(self):
        cfg = BuilderConfig("EVIDENCE_SCORING", "Scoring", {})
        assert cfg.target_engine == "evidence-engine"

    def test_target_engine_vendor_scorecard(self):
        cfg = BuilderConfig("VENDOR_SCORECARD", "Vendor", {})
        assert cfg.target_engine == "vendor-engine"

    def test_target_engine_risk_matrix(self):
        cfg = BuilderConfig("RISK_MATRIX", "Risk", {})
        assert cfg.target_engine == "risk-engine"

    def test_target_engine_dispatch_template(self):
        cfg = BuilderConfig("DISPATCH_TEMPLATE", "Dispatch", {})
        assert cfg.target_engine == "supply-chain-engine"

    def test_target_engine_readiness_gate(self):
        cfg = BuilderConfig("READINESS_GATE", "Gate", {})
        assert cfg.target_engine == "readiness-engine"

    def test_target_engine_simulation_scenario(self):
        cfg = BuilderConfig("SIMULATION_SCENARIO", "Sim", {})
        assert cfg.target_engine == "simulation-engine"

    def test_target_engine_coordination_template(self):
        cfg = BuilderConfig("COORDINATION_TEMPLATE", "Coord", {})
        assert cfg.target_engine == "coordination-engine"

    def test_target_engine_memory_pattern(self):
        cfg = BuilderConfig("MEMORY_PATTERN", "Mem", {})
        assert cfg.target_engine == "organizational-memory"

    def test_target_engine_forecast_model(self):
        cfg = BuilderConfig("FORECAST_MODEL", "Forecast", {})
        assert cfg.target_engine == "forecasting-engine"

    def test_target_engine_alignment_profile(self):
        cfg = BuilderConfig("ALIGNMENT_PROFILE", "Align", {})
        assert cfg.target_engine == "alignment-engine"

    def test_target_engine_decision_matrix(self):
        cfg = BuilderConfig("DECISION_MATRIX", "Decision", {})
        assert cfg.target_engine == "decision-engine"

    def test_target_engine_sync_policy(self):
        cfg = BuilderConfig("SYNC_POLICY", "Sync", {})
        assert cfg.target_engine == "sync-engine"

    def test_empty_config_data_allowed(self):
        cfg = BuilderConfig("WBS_TEMPLATE", "WBS", {})
        assert cfg.config_data == {}


class TestBuilderCreate:
    def test_valid_construction(self):
        bc = BuilderCreate(
            project_id=uuid.uuid4(),
            builder_type="WBS_TEMPLATE",
            name="My WBS",
        )
        assert bc.builder_type == "WBS_TEMPLATE"

    def test_invalid_builder_type_raises(self):
        with pytest.raises(Exception):
            BuilderCreate(
                project_id=uuid.uuid4(),
                builder_type="BAD_TYPE",
                name="X",
            )

    def test_empty_name_raises(self):
        with pytest.raises(Exception):
            BuilderCreate(
                project_id=uuid.uuid4(),
                builder_type="WBS_TEMPLATE",
                name="",
            )

    def test_config_data_defaults_empty(self):
        bc = BuilderCreate(
            project_id=uuid.uuid4(),
            builder_type="RISK_MATRIX",
            name="Risk",
        )
        assert bc.config_data == {}

    def test_description_defaults_none(self):
        bc = BuilderCreate(
            project_id=uuid.uuid4(),
            builder_type="RISK_MATRIX",
            name="Risk",
        )
        assert bc.description is None

    def test_all_builder_types_accepted(self):
        pid = uuid.uuid4()
        for bt in BUILDER_TYPES:
            bc = BuilderCreate(project_id=pid, builder_type=bt, name=f"Test {bt}")
            assert bc.builder_type == bt


class TestTargetEngineFor:
    def test_wbs_maps_to_core_platform(self):
        assert target_engine_for("WBS_TEMPLATE") == "core-platform"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown builder_type"):
            target_engine_for("NOT_A_BUILDER")

    def test_all_types_have_engine(self):
        for bt in BUILDER_TYPES:
            engine = target_engine_for(bt)
            assert isinstance(engine, str) and len(engine) > 0
