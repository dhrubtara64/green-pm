"""Tests for Simulation Engine service layer — S11-05."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.simulation.schemas import PerturbationSpec
from app.simulation.service import (
    ScenarioNotFoundError,
    add_perturbation,
    compute_projection,
    create_scenario,
    get_scenario,
    list_perturbations,
    list_scenarios,
)


@pytest.fixture
def session():
    s = MagicMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.scalar = AsyncMock()
    s.execute = AsyncMock()
    return s


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def project_id():
    return uuid.uuid4()


def _spec(ref: str = "ACT-001", field: str = "duration_days",
          orig: float = 10.0, pert: float = 15.0) -> PerturbationSpec:
    return PerturbationSpec(node_ref=ref, field=field,
                            original_value=orig, perturbed_value=pert)


def _empty_snapshot() -> dict:
    return {"nodes": []}


def _snapshot_with_node(ref: str = "ACT-001", dur: float = 10.0,
                        cost: float = 1000.0, pct: float = 0.0) -> dict:
    return {"nodes": [{"node_ref": ref, "duration_days": dur,
                       "cost_estimate": cost, "completion_pct": pct}]}


# ---------------------------------------------------------------------------
# create_scenario
# ---------------------------------------------------------------------------

class TestCreateScenario:
    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, project_id):
        await create_scenario(session, tenant_id, project_id, "Base")
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, project_id):
        await create_scenario(session, tenant_id, project_id, "Base")
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_status_is_draft(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "Base")
        assert scenario.status == "DRAFT"

    @pytest.mark.asyncio
    async def test_name_stored(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "Delay scenario")
        assert scenario.name == "Delay scenario"

    @pytest.mark.asyncio
    async def test_project_id_stored(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "X")
        assert scenario.project_id == project_id

    @pytest.mark.asyncio
    async def test_tenant_id_stored(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "X")
        assert scenario.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_description_none_by_default(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "X")
        assert scenario.description is None

    @pytest.mark.asyncio
    async def test_description_stored(self, session, tenant_id, project_id):
        scenario = await create_scenario(session, tenant_id, project_id, "X", description="Desc")
        assert scenario.description == "Desc"


# ---------------------------------------------------------------------------
# get_scenario
# ---------------------------------------------------------------------------

class TestGetScenario:
    @pytest.mark.asyncio
    async def test_returns_scenario_when_found(self, session, tenant_id):
        mock_scenario = MagicMock()
        session.scalar.return_value = mock_scenario
        result = await get_scenario(session, tenant_id, uuid.uuid4())
        assert result is mock_scenario

    @pytest.mark.asyncio
    async def test_raises_not_found_when_none(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(ScenarioNotFoundError):
            await get_scenario(session, tenant_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_error_message_contains_scenario_id(self, session, tenant_id):
        session.scalar.return_value = None
        sid = uuid.uuid4()
        with pytest.raises(ScenarioNotFoundError, match=str(sid)):
            await get_scenario(session, tenant_id, sid)


# ---------------------------------------------------------------------------
# list_scenarios
# ---------------------------------------------------------------------------

class TestListScenarios:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id, project_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await list_scenarios(session, tenant_id, project_id)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple(self, session, tenant_id, project_id):
        scenarios = [MagicMock(), MagicMock()]
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = scenarios
        session.execute.return_value = mock_rows
        result = await list_scenarios(session, tenant_id, project_id)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# add_perturbation
# ---------------------------------------------------------------------------

class TestAddPerturbation:
    @pytest.fixture
    def with_scenario(self, session):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        session.scalar.return_value = mock_scenario
        return mock_scenario

    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id, with_scenario):
        await add_perturbation(session, tenant_id, uuid.uuid4(), _spec())
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id, with_scenario):
        await add_perturbation(session, tenant_id, uuid.uuid4(), _spec())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_node_ref_stored(self, session, tenant_id, with_scenario):
        pert = await add_perturbation(session, tenant_id, uuid.uuid4(),
                                      _spec(ref="ACT-007"))
        assert pert.node_ref == "ACT-007"

    @pytest.mark.asyncio
    async def test_field_stored(self, session, tenant_id, with_scenario):
        pert = await add_perturbation(session, tenant_id, uuid.uuid4(),
                                      _spec(field="cost_estimate"))
        assert pert.field == "cost_estimate"

    @pytest.mark.asyncio
    async def test_original_value_stored(self, session, tenant_id, with_scenario):
        pert = await add_perturbation(session, tenant_id, uuid.uuid4(),
                                      _spec(orig=42.0))
        assert pert.original_value == 42.0

    @pytest.mark.asyncio
    async def test_perturbed_value_stored(self, session, tenant_id, with_scenario):
        pert = await add_perturbation(session, tenant_id, uuid.uuid4(),
                                      _spec(pert=99.0))
        assert pert.perturbed_value == 99.0

    @pytest.mark.asyncio
    async def test_raises_if_scenario_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(ScenarioNotFoundError):
            await add_perturbation(session, tenant_id, uuid.uuid4(), _spec())


# ---------------------------------------------------------------------------
# list_perturbations
# ---------------------------------------------------------------------------

class TestListPerturbations:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, session, tenant_id):
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = []
        session.execute.return_value = mock_rows
        result = await list_perturbations(session, tenant_id, uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_multiple(self, session, tenant_id):
        perts = [MagicMock(), MagicMock(), MagicMock()]
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = perts
        session.execute.return_value = mock_rows
        result = await list_perturbations(session, tenant_id, uuid.uuid4())
        assert len(result) == 3


# ---------------------------------------------------------------------------
# compute_projection
# ---------------------------------------------------------------------------

class TestComputeProjection:
    def _make_session_for_compute(self, session, mock_scenario, perturbations=None):
        """Wire up session.scalar → scenario, session.execute → perturbations."""
        session.scalar.return_value = mock_scenario

        perts = perturbations or []
        mock_rows = MagicMock()
        mock_rows.scalars.return_value = perts
        session.execute.return_value = mock_rows

    @pytest.mark.asyncio
    async def test_returns_projection(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        proj = await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        assert proj is not None

    @pytest.mark.asyncio
    async def test_calls_session_add(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_flush(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_schedule_delta_zero_for_empty_baseline(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        proj = await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        assert proj.schedule_delta_days == 0.0

    @pytest.mark.asyncio
    async def test_budget_delta_zero_for_empty_baseline(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        proj = await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        assert proj.budget_delta_pct == 0.0

    @pytest.mark.asyncio
    async def test_critical_path_changes_stored(self, session, tenant_id):
        mock_scenario = MagicMock()
        mock_scenario.project_id = uuid.uuid4()
        self._make_session_for_compute(session, mock_scenario)

        proj = await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
        assert isinstance(proj.critical_path_changes, dict)
        assert "affected_node_count" in proj.critical_path_changes
        assert "critical_path_affected" in proj.critical_path_changes

    @pytest.mark.asyncio
    async def test_perturbation_applied_to_projection(self, session, tenant_id):
        mock_scenario = MagicMock()
        sid = uuid.uuid4()
        mock_scenario.project_id = uuid.uuid4()

        mock_pert = MagicMock()
        mock_pert.node_ref = "ACT-001"
        mock_pert.field = "duration_days"
        mock_pert.original_value = 10.0
        mock_pert.perturbed_value = 20.0

        session.scalar.return_value = mock_scenario
        call_count = 0

        async def execute_side_effect(stmt):
            nonlocal call_count
            call_count += 1
            rows = MagicMock()
            if call_count == 1:
                rows.scalars.return_value = [mock_pert]
            else:
                rows.scalars.return_value = []
            return rows

        session.execute.side_effect = execute_side_effect

        baseline = _snapshot_with_node("ACT-001", dur=10.0, cost=1000.0)
        proj = await compute_projection(session, tenant_id, sid, baseline)
        assert proj.schedule_delta_days == 10.0

    @pytest.mark.asyncio
    async def test_raises_if_scenario_not_found(self, session, tenant_id):
        session.scalar.return_value = None
        with pytest.raises(ScenarioNotFoundError):
            await compute_projection(session, tenant_id, uuid.uuid4(), _empty_snapshot())
