"""Simulation Engine service layer — S11-05."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.simulation.model import Scenario, ScenarioPerturbation, ScenarioProjection
from app.simulation.perturbation_engine import apply_all_perturbations
from app.simulation.projection_engine import project_impacts
from app.simulation.schemas import PerturbationSpec


class ScenarioNotFoundError(Exception):
    pass


class PerturbationNotFoundError(Exception):
    pass


async def create_scenario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
) -> Scenario:
    scenario = Scenario(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        project_id=project_id,
        name=name,
        description=description,
        status="DRAFT",
    )
    session.add(scenario)
    await session.flush()
    return scenario


async def get_scenario(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Scenario:
    result = await session.scalar(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.tenant_id == tenant_id,
        )
    )
    if result is None:
        raise ScenarioNotFoundError(f"Scenario {scenario_id} not found")
    return result


async def list_scenarios(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[Scenario]:
    rows = await session.execute(
        select(Scenario).where(
            Scenario.tenant_id == tenant_id,
            Scenario.project_id == project_id,
        )
    )
    return list(rows.scalars())


async def add_perturbation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    scenario_id: uuid.UUID,
    spec: PerturbationSpec,
) -> ScenarioPerturbation:
    scenario = await get_scenario(session, tenant_id, scenario_id)
    pert = ScenarioPerturbation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        scenario_id=scenario_id,
        project_id=scenario.project_id,
        node_ref=spec.node_ref,
        field=spec.field,
        original_value=spec.original_value,
        perturbed_value=spec.perturbed_value,
    )
    session.add(pert)
    await session.flush()
    return pert


async def list_perturbations(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> list[ScenarioPerturbation]:
    rows = await session.execute(
        select(ScenarioPerturbation).where(
            ScenarioPerturbation.tenant_id == tenant_id,
            ScenarioPerturbation.scenario_id == scenario_id,
        )
    )
    return list(rows.scalars())


async def compute_projection(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    scenario_id: uuid.UUID,
    baseline: dict,
) -> ScenarioProjection:
    scenario = await get_scenario(session, tenant_id, scenario_id)

    perts = await list_perturbations(session, tenant_id, scenario_id)
    specs = [
        PerturbationSpec(
            node_ref=p.node_ref,
            field=p.field,
            original_value=p.original_value,
            perturbed_value=p.perturbed_value,
        )
        for p in perts
    ]

    perturbed = apply_all_perturbations(baseline, specs)
    result = project_impacts(scenario_id, baseline, perturbed)

    projection = ScenarioProjection(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        scenario_id=scenario_id,
        project_id=scenario.project_id,
        schedule_delta_days=result.schedule_delta_days,
        budget_delta_pct=result.budget_delta_pct,
        critical_path_changes={
            "affected_node_count": result.affected_node_count,
            "critical_path_affected": result.critical_path_affected,
        },
    )
    session.add(projection)
    await session.flush()
    return projection
