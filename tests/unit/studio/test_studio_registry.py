"""Tests for Green PM Studio builder registry — S18-01."""
import pytest

from app.studio.schemas import BUILDER_TYPES, BuilderConfig
from app.studio.registry import (
    apply_builder,
    get_default_config,
    list_builder_types,
    merge_config,
    validate_config_keys,
)


class TestGetDefaultConfig:
    def test_returns_builder_config(self):
        cfg = get_default_config("WBS_TEMPLATE")
        assert isinstance(cfg, BuilderConfig)

    def test_correct_builder_type(self):
        cfg = get_default_config("RISK_MATRIX")
        assert cfg.builder_type == "RISK_MATRIX"

    def test_non_empty_name(self):
        cfg = get_default_config("EVIDENCE_SCORING")
        assert len(cfg.name) > 0

    def test_non_empty_config_data(self):
        cfg = get_default_config("VENDOR_SCORECARD")
        assert len(cfg.config_data) > 0

    def test_all_types_have_default(self):
        for bt in BUILDER_TYPES:
            cfg = get_default_config(bt)
            assert cfg.builder_type == bt

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown builder_type"):
            get_default_config("UNKNOWN")

    def test_wbs_template_has_levels(self):
        cfg = get_default_config("WBS_TEMPLATE")
        assert "levels" in cfg.config_data

    def test_evidence_scoring_has_weights(self):
        cfg = get_default_config("EVIDENCE_SCORING")
        assert "weights" in cfg.config_data

    def test_risk_matrix_has_probability_bands(self):
        cfg = get_default_config("RISK_MATRIX")
        assert "probability_bands" in cfg.config_data

    def test_vendor_scorecard_has_dimensions(self):
        cfg = get_default_config("VENDOR_SCORECARD")
        assert "dimensions" in cfg.config_data


class TestListBuilderTypes:
    def test_returns_list(self):
        result = list_builder_types()
        assert isinstance(result, list)

    def test_length_fifteen(self):
        result = list_builder_types()
        assert len(result) == 15

    def test_is_sorted(self):
        result = list_builder_types()
        assert result == sorted(result)

    def test_all_in_builder_types(self):
        result = list_builder_types()
        assert set(result) == BUILDER_TYPES

    def test_no_duplicates(self):
        result = list_builder_types()
        assert len(result) == len(set(result))


class TestMergeConfig:
    def test_returns_dict(self):
        result = merge_config("WBS_TEMPLATE", {})
        assert isinstance(result, dict)

    def test_empty_overrides_returns_default(self):
        default = get_default_config("WBS_TEMPLATE").config_data
        merged = merge_config("WBS_TEMPLATE", {})
        assert merged == default

    def test_override_applied(self):
        merged = merge_config("WBS_TEMPLATE", {"levels": 6})
        assert merged["levels"] == 6

    def test_non_override_key_preserved(self):
        merged = merge_config("WBS_TEMPLATE", {"levels": 6})
        assert "coding_scheme" in merged

    def test_new_key_added(self):
        merged = merge_config("WBS_TEMPLATE", {"custom_field": "yes"})
        assert merged["custom_field"] == "yes"

    def test_does_not_mutate_original(self):
        before = dict(get_default_config("WBS_TEMPLATE").config_data)
        merge_config("WBS_TEMPLATE", {"levels": 99})
        after = get_default_config("WBS_TEMPLATE").config_data
        assert after == before

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown builder_type"):
            merge_config("INVALID", {})


class TestValidateConfigKeys:
    def test_empty_config_returns_empty(self):
        unknown = validate_config_keys("WBS_TEMPLATE", {})
        assert unknown == []

    def test_known_key_not_flagged(self):
        unknown = validate_config_keys("WBS_TEMPLATE", {"levels": 4})
        assert "levels" not in unknown

    def test_unknown_key_flagged(self):
        unknown = validate_config_keys("WBS_TEMPLATE", {"alien_key": True})
        assert "alien_key" in unknown

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            validate_config_keys("BAD_TYPE", {})

    def test_multiple_unknown_keys(self):
        unknown = validate_config_keys("WBS_TEMPLATE", {"x": 1, "y": 2})
        assert len(unknown) == 2


class TestApplyBuilder:
    def test_returns_target(self):
        class FakeTarget:
            pass
        t = FakeTarget()
        result = apply_builder("WBS_TEMPLATE", {}, t)
        assert result is t

    def test_calls_apply_config_if_present(self):
        class SmartTarget:
            called = False
            def apply_config(self, builder_type, config):
                SmartTarget.called = True
        t = SmartTarget()
        apply_builder("WBS_TEMPLATE", {}, t)
        assert SmartTarget.called

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown builder_type"):
            apply_builder("INVALID", {}, object())
