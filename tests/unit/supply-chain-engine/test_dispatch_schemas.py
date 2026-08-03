"""Tests for dispatch schemas and domain constants — S7-01."""
import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.dispatch.schemas import (
    _CRITICALITY_WEIGHT,
    _DISPATCH_STAGES,
    _STAGE_INDEX,
    _SUPPLY_CHAIN_TOPIC,
    _VALID_TRANSITIONS,
    DispatchCreate,
    DispatchResponse,
    MaterialItemCreate,
    MaterialItemResponse,
    MaterialPackageCreate,
    MaterialPackageResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    StageTransitionRequest,
    StageTransitionResponse,
    VendorCreate,
    VendorResponse,
)


class TestDomainConstants:
    def test_dispatch_stages_has_10_stages(self):
        assert len(_DISPATCH_STAGES) == 10

    def test_dispatch_stages_first_is_po_raised(self):
        assert _DISPATCH_STAGES[0] == "PO_RAISED"

    def test_dispatch_stages_last_is_accepted(self):
        assert _DISPATCH_STAGES[-1] == "ACCEPTED"

    def test_dispatch_stages_contains_all_expected(self):
        expected = {
            "PO_RAISED", "VENDOR_CONFIRMED", "MANUFACTURING", "QC_INSPECTION",
            "READY_FOR_DISPATCH", "DISPATCHED", "IN_TRANSIT",
            "ARRIVED_AT_SITE", "INSPECTED_ON_SITE", "ACCEPTED",
        }
        assert set(_DISPATCH_STAGES) == expected

    def test_valid_transitions_has_10_entries(self):
        assert len(_VALID_TRANSITIONS) == 10

    def test_valid_transitions_first_stage_points_to_second(self):
        assert _VALID_TRANSITIONS["PO_RAISED"] == "VENDOR_CONFIRMED"

    def test_valid_transitions_terminal_stage_is_none(self):
        assert _VALID_TRANSITIONS["ACCEPTED"] is None

    def test_valid_transitions_sequential(self):
        for i, stage in enumerate(_DISPATCH_STAGES[:-1]):
            assert _VALID_TRANSITIONS[stage] == _DISPATCH_STAGES[i + 1]

    def test_stage_index_maps_po_raised_to_zero(self):
        assert _STAGE_INDEX["PO_RAISED"] == 0

    def test_stage_index_maps_accepted_to_nine(self):
        assert _STAGE_INDEX["ACCEPTED"] == 9

    def test_stage_index_monotone(self):
        for i, stage in enumerate(_DISPATCH_STAGES):
            assert _STAGE_INDEX[stage] == i

    def test_supply_chain_topic(self):
        assert _SUPPLY_CHAIN_TOPIC == "greenpm.supply"

    def test_criticality_weight(self):
        assert _CRITICALITY_WEIGHT == 2.0


class TestVendorSchemas:
    def test_vendor_create_stores_name_and_project_id(self):
        pid = uuid.uuid4()
        v = VendorCreate(name="ACME Corp", project_id=pid)
        assert v.name == "ACME Corp"
        assert v.project_id == pid

    def test_vendor_create_optional_fields_default_none(self):
        v = VendorCreate(name="X", project_id=uuid.uuid4())
        assert v.contact_email is None
        assert v.vendor_code is None

    def test_vendor_response_from_attributes(self):
        assert VendorResponse.model_config.get("from_attributes") is True


class TestPurchaseOrderSchemas:
    def test_po_create_stores_po_number(self):
        po = PurchaseOrderCreate(
            vendor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            po_number="PO-001",
            total_value=5000.0,
        )
        assert po.po_number == "PO-001"
        assert po.total_value == 5000.0

    def test_po_create_default_currency_usd(self):
        po = PurchaseOrderCreate(
            vendor_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            po_number="PO-002",
            total_value=100.0,
        )
        assert po.currency == "USD"

    def test_po_create_negative_value_raises(self):
        with pytest.raises(ValidationError):
            PurchaseOrderCreate(
                vendor_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                po_number="PO-003",
                total_value=-1.0,
            )


class TestDispatchSchemas:
    def test_dispatch_create_stores_fields(self):
        d = DispatchCreate(
            po_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            dispatch_number="DISP-001",
        )
        assert d.dispatch_number == "DISP-001"

    def test_dispatch_response_from_attributes(self):
        assert DispatchResponse.model_config.get("from_attributes") is True

    def test_stage_transition_request_stores_target_stage(self):
        req = StageTransitionRequest(target_stage="VENDOR_CONFIRMED")
        assert req.target_stage == "VENDOR_CONFIRMED"


class TestMaterialSchemas:
    def test_material_package_create_stores_package_number(self):
        mp = MaterialPackageCreate(
            dispatch_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            package_number="PKG-001",
        )
        assert mp.package_number == "PKG-001"

    def test_material_item_create_stores_description_and_quantity(self):
        mi = MaterialItemCreate(
            package_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            description="Steel beam 10m",
            quantity=5.0,
            unit="pcs",
        )
        assert mi.description == "Steel beam 10m"
        assert mi.quantity == 5.0
        assert mi.unit == "pcs"

    def test_material_item_create_activity_id_optional(self):
        mi = MaterialItemCreate(
            package_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            description="Bolt",
            quantity=100.0,
            unit="pcs",
        )
        assert mi.activity_id is None

    def test_material_item_create_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            MaterialItemCreate(
                package_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                description="Bolt",
                quantity=0.0,
                unit="pcs",
            )

    def test_material_item_response_from_attributes(self):
        assert MaterialItemResponse.model_config.get("from_attributes") is True
