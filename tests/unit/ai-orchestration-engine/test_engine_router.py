"""Tests for NL query engine routing — S16-02."""
import pytest

from app.ai.router import (
    _FALLBACK_ENGINE,
    route_query,
    synthesize_responses,
)


class TestRouteQuery:
    def test_empty_string_returns_empty(self):
        assert route_query("") == []

    def test_whitespace_only_returns_empty(self):
        assert route_query("   ") == []

    def test_returns_list(self):
        result = route_query("What are the risks?")
        assert isinstance(result, list)

    def test_risk_keyword_routes_to_risk_engine(self):
        result = route_query("What is the project risk exposure?")
        assert "risk-engine" in result

    def test_dependency_keyword_routes_correctly(self):
        result = route_query("Show me the critical path and dependencies")
        assert "dependency-engine" in result

    def test_vendor_keyword_routes_correctly(self):
        result = route_query("What is the vendor scorecard this month?")
        assert "vendor-engine" in result

    def test_forecast_keyword_routes_correctly(self):
        result = route_query("Show me the project forecast and trend")
        assert "forecasting-engine" in result

    def test_decision_keyword_routes_correctly(self):
        result = route_query("Which decisions are pending approval?")
        assert "decision-engine" in result

    def test_simulation_keyword_routes_correctly(self):
        result = route_query("Run a what-if simulation scenario")
        assert "simulation-engine" in result

    def test_no_match_returns_fallback(self):
        result = route_query("xyzzy plugh frobozz")
        assert result == [_FALLBACK_ENGINE]

    def test_fallback_is_core_platform(self):
        assert _FALLBACK_ENGINE == "core-platform"

    def test_max_engines_limits_results(self):
        result = route_query(
            "risk vendor dependency supply simulation coordination",
            max_engines=2,
        )
        assert len(result) <= 2

    def test_max_engines_one(self):
        result = route_query("risk vendor", max_engines=1)
        assert len(result) == 1

    def test_multiple_keyword_hits_rank_higher(self):
        # query has 3 risk keywords vs 1 vendor keyword
        result = route_query("risk threat hazard vendor", max_engines=2)
        assert result[0] == "risk-engine"

    def test_alignment_keyword_routes_correctly(self):
        result = route_query("Is there a stakeholder alignment gap?")
        assert "alignment-engine" in result

    def test_readiness_keyword_routes_correctly(self):
        result = route_query("Is the system ready for go-live?")
        assert "readiness-engine" in result

    def test_memory_keyword_routes_correctly(self):
        result = route_query("Are there relevant lessons learned patterns?")
        assert "organizational-memory" in result

    def test_supply_keyword_routes_correctly(self):
        result = route_query("What is the supply chain status for materials?")
        assert "supply-chain-engine" in result

    def test_sync_keyword_routes_correctly(self):
        result = route_query("Check for inconsistency and contradictions in the graph")
        assert "sync-engine" in result

    def test_evidence_keyword_routes_correctly(self):
        result = route_query("Show all evidence documents and scores")
        assert "evidence-engine" in result

    def test_pig_keyword_routes_correctly(self):
        result = route_query("Traverse the PIG graph nodes and edges")
        assert "pig-service" in result

    def test_impact_keyword_routes_correctly(self):
        result = route_query("What is the cascade impact of this change?")
        assert "impact-engine" in result

    def test_result_contains_no_duplicates(self):
        result = route_query("risk risk risk threat threat", max_engines=5)
        assert len(result) == len(set(result))

    def test_max_engines_equal_to_total_engines(self):
        result = route_query(
            "risk impact dependency supply vendor readiness simulation coordination memory forecast alignment decision sync evidence pig project",
            max_engines=16,
        )
        assert len(result) <= 16

    def test_case_insensitive(self):
        lower = route_query("risk analysis")
        upper = route_query("RISK ANALYSIS")
        assert set(lower) == set(upper)


class TestSynthesizeResponses:
    def test_empty_dict_returns_no_info_message(self):
        result = synthesize_responses({})
        assert "No relevant" in result

    def test_single_engine_returns_its_response(self):
        result = synthesize_responses({"engine-a": "Analysis A."})
        assert result == "Analysis A."

    def test_multiple_engines_combined(self):
        result = synthesize_responses({
            "engine-a": "Part one.",
            "engine-b": "Part two.",
        })
        assert "Part one" in result
        assert "Part two" in result

    def test_engine_keys_not_in_output(self):
        result = synthesize_responses({
            "risk-engine": "Risks are moderate.",
            "vendor-engine": "Vendors performing well.",
        })
        assert "risk-engine" not in result
        assert "vendor-engine" not in result

    def test_returns_string(self):
        result = synthesize_responses({"engine-a": "content"})
        assert isinstance(result, str)

    def test_all_empty_values_returns_no_info(self):
        result = synthesize_responses({"engine-a": "  ", "engine-b": ""})
        assert "No relevant" in result

    def test_three_sources_combined(self):
        result = synthesize_responses({
            "a": "Alpha.",
            "b": "Beta.",
            "c": "Gamma.",
        })
        assert "Alpha" in result
        assert "Beta" in result
        assert "Gamma" in result
