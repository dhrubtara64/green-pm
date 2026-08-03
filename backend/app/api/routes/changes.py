"""Change Register — static demo data for Bellary CCGT Power Project."""
from fastapi import APIRouter

router = APIRouter(prefix="/changes", tags=["changes"])

CHANGES = [
    {
        "id": "NCR-2024-E-041",
        "type": "NCR",
        "description": "MCC Room cabling — claimed 55%, CEIG inspection finds 30–35%",
        "status": "Open",
        "days_open": 12,
        "value": None,
        "value_label": "TBD",
        "affected_activity_id": "act-032",
        "affected_activity_name": "MCC Room Cabling Installation (WBS 4.3)",
        "ai_flag": "Milestone risk",
        "ai_flag_level": "danger",
        "root_cause": "Carrot Controls & Electrical claimed 55% on MCC cabling. CEIG pre-inspection found motor control cables unterminated on 12 of 24 boards. Actual completion 30–35%.",
        "cost_impact": "₹50.9 L overcharge risk (claimed ₹1.29 Cr, approved ₹78.3 L)",
        "timeline": [
            {"date": "18 Nov 2024", "event": "QC Inspection finds 30–35% actual vs 55% claimed"},
            {"date": "19 Nov 2024", "event": "NCR-2024-E-041 raised by QC Manager Kavita Reddy"},
            {"date": "22 Nov 2024", "event": "Carrot Controls & Electrical notified — response pending"},
        ],
    },
    {
        "id": "RFI-2024-047",
        "type": "RFI",
        "description": "GT Foundation waterproofing membrane spec (IS 2645) — awaiting MECON Engineering response",
        "status": "Open",
        "days_open": 34,
        "value": None,
        "value_label": "TBD (~₹4.2 L)",
        "affected_activity_id": "act-003",
        "affected_activity_name": "GT Foundation Concrete Pour (WBS 1.3)",
        "ai_flag": "Delays pour cert",
        "ai_flag_level": "warn",
        "root_cause": "Waterproofing membrane spec IS 2645 has two acceptable grades. Drawings did not specify which grade. MECON Engineering clarification required before procurement.",
        "cost_impact": "TBD — grade difference ~₹4.2 L",
        "timeline": [
            {"date": "26 Jun 2026", "event": "RFI submitted to MECON Engineering for IS 2645 grade clarification"},
            {"date": "10 Jul 2026", "event": "MECON acknowledged — target response 28 Jul"},
            {"date": "28 Jul 2026", "event": "Response overdue — follow-up issued"},
        ],
    },
    {
        "id": "VO-2024-011",
        "type": "VO",
        "description": "Additional earthing conductor runs — scope extension per CEA Technical Standards",
        "status": "Open",
        "days_open": 9,
        "value": "₹1.05 Cr",
        "value_label": "₹1.05 Cr",
        "affected_activity_id": "act-035",
        "affected_activity_name": "Earthing and Lightning Protection (WBS 4.6)",
        "ai_flag": "Pending approval",
        "ai_flag_level": "warn",
        "root_cause": "CEA Technical Standards revision (2023) introduced additional earthing conductor requirements not in original scope. Gap identified during CEIG pre-inspection.",
        "cost_impact": "₹1.05 Cr pending approval",
        "timeline": [
            {"date": "21 Jul 2026", "event": "CEA standard gap identified during CEIG pre-inspection"},
            {"date": "25 Jul 2026", "event": "VO pricing submitted by Carrot Controls: ₹1.05 Cr"},
            {"date": "29 Jul 2026", "event": "Client review in progress"},
        ],
    },
    {
        "id": "TQ-2024-088",
        "type": "TQ",
        "description": "HRSG drum alignment tolerance — Brinjal Mechanical query on IBR vs OEM acceptance criteria",
        "status": "Open",
        "days_open": 12,
        "value": None,
        "value_label": "—",
        "affected_activity_id": "act-013",
        "affected_activity_name": "HRSG Drum and Header Installation (WBS 2.4)",
        "ai_flag": "Reliability concern",
        "ai_flag_level": "warn",
        "root_cause": "IBR (Indian Boiler Regulations) stipulate drum alignment tolerances differently from OEM spec. Brinjal Mechanical seeking clarification on which standard governs.",
        "cost_impact": "No direct cost — potential rework risk if resolved unfavourably",
        "timeline": [
            {"date": "18 Jul 2026", "event": "TQ raised by Brinjal Mechanical on IBR vs OEM tolerances"},
            {"date": "24 Jul 2026", "event": "QC Manager escalated to IBR inspection authority"},
            {"date": "30 Jul 2026", "event": "IBR inspector site visit scheduled — 05 Aug"},
        ],
    },
    {
        "id": "VO-2024-009",
        "type": "VO",
        "description": "Fireproofing scope addition on structural steel — Bay A & B (OISD-STD-116)",
        "status": "Approved",
        "days_open": 28,
        "value": "₹74 L",
        "value_label": "₹74 L",
        "affected_activity_id": "act-004",
        "affected_activity_name": "HRSG Structural Steelwork — Bay A (WBS 1.4)",
        "ai_flag": "Incorporated",
        "ai_flag_level": "clear",
        "root_cause": "OISD-STD-116 fireproofing requirement on structural steel in hydrocarbon areas not in original scope. Added after OISD audit.",
        "cost_impact": "₹74 L (approved)",
        "timeline": [
            {"date": "02 Jun 2026", "event": "OISD audit identified fireproofing gap — Bay A & B"},
            {"date": "08 Jun 2026", "event": "VO pricing submitted by Mango Civil Works: ₹74 L"},
            {"date": "01 Jul 2026", "event": "Client approved VO — works incorporated"},
        ],
    },
    {
        "id": "CO-2024-003",
        "type": "CO",
        "description": "Cooling water pipe route modification — clash with underground KPTCL cable services",
        "status": "Approved",
        "days_open": 45,
        "value": "₹1.28 Cr",
        "value_label": "₹1.28 Cr",
        "affected_activity_id": "act-024",
        "affected_activity_name": "Cooling Water Piping Installation (WBS 3.5)",
        "ai_flag": "Incorporated",
        "ai_flag_level": "clear",
        "root_cause": "Underground KPTCL HT cable discovered during excavation — not shown on client-issued drawings. Cooling water pipe rerouted to avoid clash.",
        "cost_impact": "₹1.28 Cr (approved)",
        "timeline": [
            {"date": "15 May 2026", "event": "KPTCL cable discovered during trench excavation"},
            {"date": "22 May 2026", "event": "Survey completed — revised route agreed with KPTCL"},
            {"date": "01 Jun 2026", "event": "Client approved revised route and CO: ₹1.28 Cr"},
        ],
    },
]


@router.get("")
def list_changes():
    return CHANGES


@router.get("/summary")
def changes_summary():
    open_items = [c for c in CHANGES if c["status"] == "Open"]
    ncrs = [c for c in open_items if c["type"] == "NCR"]
    pending_value = sum(
        0 for c in open_items
        if c["value"] and "Cr" in c["value"]
    )
    return {
        "total": len(CHANGES),
        "open": len(open_items),
        "open_ncrs": len(ncrs),
        "max_days_open": max((c["days_open"] for c in open_items), default=0),
        "pending_vo_value": "₹1.05 Cr",
        "approved_vo_value": "₹2.03 Cr",
    }
