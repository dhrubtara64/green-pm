"""
Seed data generator for the Green PM demo.

Project: Bellary CCGT Power Project — 900 MW
Client: Bellary Power Ltd · Project No. BPL-CCG-2024
Location: Bellary, Karnataka
Sector: Power generation (gas turbine + steam turbine + HRSG)
Scale: ~40 activities across Civil, Mechanical, Piping, Electrical, I&C, Commissioning

Subcontractors:
  Mango Civil Works          — Civil & structural
  Guava Power Services       — Gas turbine package
  Brinjal Mechanical Systems — HRSG, steam turbine, condenser
  Carrot Controls & Electrical — Electrical systems (MCC, cabling, transformer)
  Avocado Automation         — DCS / I&C
  Turnip Engineering         — Commissioning & pre-commissioning

Demo scenarios per Product Bible / diagram 17:
  A — GT receipt: 3 corroborating sources, clean history → Ev≈0.85, Conf≈0.85
  B — HRSG drum: 3 sources agree, BAD vendor history → Ev≈0.80, Conf≈0.35 [KEY DIVERGENCE]
  C — GT foundation concrete: 1 stale source → Ev≈0.20, Conf≈0.30 [LOW-LOW]
  D — HP steam hydro test: 1 fresh highly-reliable source → Ev≈0.30, Conf≈0.75
  E — MCC cabling: contradicting evidence (CEIG NCR) → Verification Required

Run with: python seed/generate_seed_data.py
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://greenpm:greenpm@localhost:5432/greenpm")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

from app.database import Base
from app.models.activity import Activity
from app.models.milestone import Milestone
from app.models.deliverable import Deliverable
from app.models.evidence_item import EvidenceItem, SourceReliabilitySignal, RelationType
from app.models.associations import (
    activity_evidence_items,
    activity_milestones,
    deliverable_evidence_items,
)
from app.models.human_correction import HumanCorrection
from app.models.weekly_report import WeeklyReport


def ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def clear_existing(session):
    session.execute(activity_evidence_items.delete())
    session.execute(activity_milestones.delete())
    session.execute(deliverable_evidence_items.delete())
    session.query(HumanCorrection).delete()
    session.query(WeeklyReport).delete()
    session.query(EvidenceItem).delete()
    session.query(Activity).delete()
    session.query(Milestone).delete()
    session.query(Deliverable).delete()
    session.commit()


def seed(session):
    print("Seeding Bellary CCGT Power Project (900 MW)...")

    # -------------------------------------------------------------------------
    # MILESTONES
    # -------------------------------------------------------------------------
    milestones = [
        Milestone(id="ms-001", name="Civil Works Complete", target_date=date(2025, 6, 30)),
        Milestone(id="ms-002", name="Mechanical Equipment Installation Complete", target_date=date(2025, 9, 30)),
        Milestone(id="ms-003", name="Piping Pressure Test Complete", target_date=date(2025, 11, 30)),
        Milestone(id="ms-004", name="Electrical Systems Energized", target_date=date(2026, 1, 31)),
        Milestone(id="ms-005", name="Cold Commissioning Complete", target_date=date(2026, 3, 31)),
        Milestone(id="ms-006", name="First Fire", target_date=date(2026, 5, 31)),
    ]
    session.add_all(milestones)

    # -------------------------------------------------------------------------
    # DELIVERABLES
    # -------------------------------------------------------------------------
    deliverables = [
        Deliverable(id="del-001", name="Gas Turbine Foundation Drawing", type="drawing", status="approved"),
        Deliverable(id="del-002", name="HRSG Structural Drawing Package", type="drawing", status="approved"),
        Deliverable(id="del-003", name="Main Transformer Procurement Package", type="document", status="in_progress"),
        Deliverable(id="del-004", name="Piping Isometric Drawings — High Pressure Steam", type="drawing", status="in_progress"),
        Deliverable(id="del-005", name="DCS Configuration Specification", type="document", status="submitted"),
        Deliverable(id="del-006", name="Electrical Single Line Diagram", type="drawing", status="approved"),
        Deliverable(id="del-007", name="MCC Room Layout Drawing", type="drawing", status="approved"),
        Deliverable(id="del-008", name="Condenser BOQ Package", type="document", status="pending"),
    ]
    session.add_all(deliverables)

    # -------------------------------------------------------------------------
    # ACTIVITIES (40 total across all disciplines)
    # -------------------------------------------------------------------------

    # --- CIVIL (WBS 1.x) — Mango Civil Works ---
    act_civil = [
        Activity(id="act-001", name="Site Preparation and Clearing", wbs_ref="1.1", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=100.0, source_schedule_ref="TSK-001"),
        Activity(id="act-002", name="Gas Turbine Foundation Excavation", wbs_ref="1.2", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=100.0, source_schedule_ref="TSK-002"),
        # SCENARIO C: stale single source
        Activity(id="act-003", name="Gas Turbine Foundation Concrete Pour", wbs_ref="1.3", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=85.0, source_schedule_ref="TSK-003"),
        Activity(id="act-004", name="HRSG Structural Steelwork — Bay A", wbs_ref="1.4", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=70.0, source_schedule_ref="TSK-004"),
        Activity(id="act-005", name="HRSG Structural Steelwork — Bay B", wbs_ref="1.5", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=55.0, source_schedule_ref="TSK-005"),
        Activity(id="act-006", name="Control Building Foundation", wbs_ref="1.6", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=100.0, source_schedule_ref="TSK-006"),
        Activity(id="act-007", name="Cooling Water Pipe Trench Excavation", wbs_ref="1.7", discipline="Civil",
                 subcontractor="Mango Civil Works", reported_progress=90.0, source_schedule_ref="TSK-007"),
    ]

    # --- MECHANICAL (WBS 2.x) ---
    act_mech = [
        # SCENARIO A: 3 corroborating sources, clean history — Guava Power Services (GT package)
        Activity(id="act-010", name="Gas Turbine Package Receipt and Inspection", wbs_ref="2.1", discipline="Mechanical",
                 subcontractor="Guava Power Services", reported_progress=100.0, source_schedule_ref="TSK-010"),
        Activity(id="act-011", name="Gas Turbine Baseframe Setting", wbs_ref="2.2", discipline="Mechanical",
                 subcontractor="Guava Power Services", reported_progress=100.0, source_schedule_ref="TSK-011"),
        Activity(id="act-012", name="Gas Turbine Alignment and Grouting", wbs_ref="2.3", discipline="Mechanical",
                 subcontractor="Guava Power Services", reported_progress=75.0, source_schedule_ref="TSK-012"),
        # SCENARIO B: 3 sources agree but BAD vendor history — Brinjal Mechanical Systems
        Activity(id="act-013", name="HRSG Drum and Header Installation", wbs_ref="2.4", discipline="Mechanical",
                 subcontractor="Brinjal Mechanical Systems", reported_progress=60.0, source_schedule_ref="TSK-013"),
        Activity(id="act-014", name="Steam Turbine Package Receipt and Inspection", wbs_ref="2.5", discipline="Mechanical",
                 subcontractor="Brinjal Mechanical Systems", reported_progress=40.0, source_schedule_ref="TSK-014"),
        Activity(id="act-015", name="Condenser Installation", wbs_ref="2.6", discipline="Mechanical",
                 subcontractor="Brinjal Mechanical Systems", reported_progress=30.0, source_schedule_ref="TSK-015"),
        Activity(id="act-016", name="Lube Oil System Installation", wbs_ref="2.7", discipline="Mechanical",
                 subcontractor="Brinjal Mechanical Systems", reported_progress=20.0, source_schedule_ref="TSK-016"),
        Activity(id="act-017", name="Fuel Gas System Installation", wbs_ref="2.8", discipline="Mechanical",
                 subcontractor="Brinjal Mechanical Systems", reported_progress=15.0, source_schedule_ref="TSK-017"),
    ]

    # --- PIPING (WBS 3.x) — Mango Civil Works ---
    act_piping = [
        Activity(id="act-020", name="HP Steam Piping Fabrication", wbs_ref="3.1", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=65.0, source_schedule_ref="TSK-020"),
        Activity(id="act-021", name="HP Steam Piping Erection and Supports", wbs_ref="3.2", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=45.0, source_schedule_ref="TSK-021"),
        # SCENARIO D: single fresh highly-reliable source
        Activity(id="act-022", name="HP Steam Piping Hydrostatic Test", wbs_ref="3.3", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=0.0, source_schedule_ref="TSK-022"),
        Activity(id="act-023", name="LP Steam Piping Fabrication and Erection", wbs_ref="3.4", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=35.0, source_schedule_ref="TSK-023"),
        Activity(id="act-024", name="Cooling Water Piping Installation", wbs_ref="3.5", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=50.0, source_schedule_ref="TSK-024"),
        Activity(id="act-025", name="Fuel Gas Piping Installation", wbs_ref="3.6", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=30.0, source_schedule_ref="TSK-025"),
        Activity(id="act-026", name="Auxiliary Piping and Fittings", wbs_ref="3.7", discipline="Piping",
                 subcontractor="Mango Civil Works", reported_progress=20.0, source_schedule_ref="TSK-026"),
    ]

    # --- ELECTRICAL (WBS 4.x) — Carrot Controls & Electrical ---
    act_elec = [
        Activity(id="act-030", name="Main Transformer Receipt and Inspection", wbs_ref="4.1", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=100.0, source_schedule_ref="TSK-030"),
        Activity(id="act-031", name="Main Transformer Installation and Commissioning", wbs_ref="4.2", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=80.0, source_schedule_ref="TSK-031"),
        # SCENARIO E: contradicting evidence (CEIG NCR) → Verification Required
        Activity(id="act-032", name="MCC Room Cabling Installation", wbs_ref="4.3", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=55.0, source_schedule_ref="TSK-032"),
        Activity(id="act-033", name="Cable Pulling and Termination — GT Area", wbs_ref="4.4", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=40.0, source_schedule_ref="TSK-033"),
        Activity(id="act-034", name="Cable Pulling and Termination — ST Area", wbs_ref="4.5", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=25.0, source_schedule_ref="TSK-034"),
        Activity(id="act-035", name="Earthing and Lightning Protection", wbs_ref="4.6", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=70.0, source_schedule_ref="TSK-035"),
        Activity(id="act-036", name="Lighting and Small Power Installation", wbs_ref="4.7", discipline="Electrical",
                 subcontractor="Carrot Controls & Electrical", reported_progress=35.0, source_schedule_ref="TSK-036"),
    ]

    # --- INSTRUMENTATION & CONTROL (WBS 5.x) — Avocado Automation ---
    act_ic = [
        Activity(id="act-040", name="DCS Cabinet Installation and Wiring", wbs_ref="5.1", discipline="I&C",
                 subcontractor="Avocado Automation", reported_progress=60.0, source_schedule_ref="TSK-040"),
        Activity(id="act-041", name="Field Instrument Installation — GT Area", wbs_ref="5.2", discipline="I&C",
                 subcontractor="Avocado Automation", reported_progress=45.0, source_schedule_ref="TSK-041"),
        Activity(id="act-042", name="Field Instrument Installation — ST Area", wbs_ref="5.3", discipline="I&C",
                 subcontractor="Avocado Automation", reported_progress=30.0, source_schedule_ref="TSK-042"),
        Activity(id="act-043", name="DCS Configuration and FAT", wbs_ref="5.4", discipline="I&C",
                 subcontractor="Avocado Automation", reported_progress=20.0, source_schedule_ref="TSK-043"),
        Activity(id="act-044", name="CEMS (Continuous Emission Monitoring) Installation", wbs_ref="5.5", discipline="I&C",
                 subcontractor="Avocado Automation", reported_progress=10.0, source_schedule_ref="TSK-044"),
    ]

    # --- COMMISSIONING (WBS 6.x) — Turnip Engineering ---
    act_comm = [
        Activity(id="act-050", name="Pre-Commissioning Checks — Civil and Structural", wbs_ref="6.1", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=80.0, source_schedule_ref="TSK-050"),
        Activity(id="act-051", name="Pre-Commissioning Checks — Mechanical Rotating", wbs_ref="6.2", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=40.0, source_schedule_ref="TSK-051"),
        Activity(id="act-052", name="Pre-Commissioning Checks — Electrical", wbs_ref="6.3", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=25.0, source_schedule_ref="TSK-052"),
        Activity(id="act-053", name="Flushing and Chemical Cleaning — Water Systems", wbs_ref="6.4", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=0.0, source_schedule_ref="TSK-053"),
        Activity(id="act-054", name="Cold Commissioning — GT Auxiliaries", wbs_ref="6.5", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=0.0, source_schedule_ref="TSK-054"),
        Activity(id="act-055", name="First Fire and Initial Operation", wbs_ref="6.6", discipline="Commissioning",
                 subcontractor="Turnip Engineering", reported_progress=0.0, source_schedule_ref="TSK-055"),
    ]

    all_activities = act_civil + act_mech + act_piping + act_elec + act_ic + act_comm
    session.add_all(all_activities)
    session.flush()

    # -------------------------------------------------------------------------
    # EVIDENCE ITEMS — engineered for specific demo scenarios
    # -------------------------------------------------------------------------

    evidence_items = []

    # --- SCENARIO A: act-010 — GT Receipt (Evidence 0.85, Confidence 0.85) ---
    ev_a1 = EvidenceItem(
        id="ev-a1",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="GT_Receipt_Inspection_Report_Bellary_2024-11-15.pdf",
        extracted_content="Gas Turbine Model GE 9HA.01 received at Bellary site. Serial No. 7A4129. "
                          "Visual inspection completed. All major components accounted for. No transit damage observed. "
                          "Signed: Site Inspector A. Kumar, QA Lead P. Sharma. Date: 15 Nov 2024.",
        source_excerpt="GT receipt inspection complete. No damage. QA signed off 15 Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.high,
        timestamp=ago(10),
    )
    ev_a2 = EvidenceItem(
        id="ev-a2",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Transmittal_GE_9HA01_Delivery_Confirmation_Bellary.pdf",
        extracted_content="Delivery Transmittal No. TRS-2024-447. GE Gas Turbine Package confirmed delivered "
                          "to Bellary Power Station. 100% of line items confirmed received and checked against "
                          "packing list. Accepted by Client Representative — Bellary Power Ltd.",
        source_excerpt="100% of GT Package line items received and accepted per TRS-2024-447.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.high,
        timestamp=ago(12),
    )
    ev_a3 = EvidenceItem(
        id="ev-a3",
        source_system="schedule_xer",
        ingesting_connector="schedule_xer_ingestor_v1",
        provenance_ref="Bellary_CCGT_P6_Export_2024-11-20.xer",
        extracted_content="TASK TSK-010: Gas Turbine Package Receipt and Inspection. "
                          "Status: Complete. Actual Finish: 18-Nov-2024. Physical % Complete: 100%.",
        source_excerpt="P6 Schedule: TSK-010 marked 100% complete. Actual finish 18 Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.medium,
        timestamp=ago(7),
    )
    evidence_items.extend([ev_a1, ev_a2, ev_a3])

    # --- SCENARIO B: act-013 — HRSG Drum (Evidence 0.80, Confidence 0.35) ---
    # 3 sources agree but all from Brinjal Mechanical Systems (history of overclaiming)
    ev_b1 = EvidenceItem(
        id="ev-b1",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Brinjal_Mechanical_India_Progress_Report_Nov_2024.pdf",
        extracted_content="Brinjal Mechanical Systems Progress Report — November 2024. HRSG Drum and Header "
                          "installation: 60% complete. Drums 1 and 2 positioned on HRSG structure. "
                          "Header connections in progress. IBR TQ raised on drum alignment tolerance.",
        source_excerpt="Brinjal self-report: HRSG drum installation 60% complete. Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.low,
        timestamp=ago(5),
    )
    ev_b2 = EvidenceItem(
        id="ev-b2",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Brinjal_Mechanical_India_Site_Photo_Bellary_2024-11-18.pdf",
        extracted_content="Site photo documentation — HRSG installation area, Bellary site. Photos show Drum 1 and "
                          "Drum 2 in position on HRSG structure. Steam headers partially connected. "
                          "Photo timestamp 18-Nov-2024. Estimated progress: 58–62%.",
        source_excerpt="Site photos confirm HRSG drums positioned, headers partial. ~60% progress. 18 Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.low,
        timestamp=ago(9),
    )
    ev_b3 = EvidenceItem(
        id="ev-b3",
        source_system="schedule_xer",
        ingesting_connector="schedule_xer_ingestor_v1",
        provenance_ref="Bellary_CCGT_P6_Export_2024-11-20.xer",
        extracted_content="TASK TSK-013: HRSG Drum and Header Installation. Physical % Complete: 60%. "
                          "Note: Progress entered by Brinjal Mechanical site representative. "
                          "Not independently verified this period.",
        source_excerpt="P6: TSK-013 at 60%. Input from Brinjal Mechanical — not independently verified.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.medium,
        timestamp=ago(7),
    )
    evidence_items.extend([ev_b1, ev_b2, ev_b3])

    # --- SCENARIO C: act-003 — GT Foundation Concrete Pour (Evidence 0.20, Confidence 0.30) ---
    ev_c1 = EvidenceItem(
        id="ev-c1",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Site_Weekly_Update_Bellary_2024-10-04.txt",
        extracted_content="Weekly site update 4-Oct-2024: GT foundation concrete pour in progress. "
                          "Approximately 85% of concrete placed. Remaining 15% planned for next week. "
                          "RFI-2024-047 open on IS 2645 waterproofing spec. Source: Site foreman verbal update.",
        source_excerpt="GT foundation concrete pour ~85%. Foreman verbal update, 4 Oct 2024. IS 2645 RFI open.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.low,
        timestamp=ago(28),
    )
    evidence_items.append(ev_c1)

    # --- SCENARIO D: act-022 — HP Steam Hydro Test (Evidence 0.30, Confidence 0.75) ---
    ev_d1 = EvidenceItem(
        id="ev-d1",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="HP_Steam_Hydro_Test_Witness_Record_Bellary_2024-11-22.pdf",
        extracted_content="HYDROSTATIC TEST WITNESS RECORD. Line: HP Steam Main — BLY-HS-001. "
                          "Test Pressure: 145 bar. Hold time: 1 hour. Result: PASS. No leaks detected. "
                          "Witnessed by Bureau Veritas — Cert No. BV-2024-BL-0471. "
                          "Client Representative: R. Nair, PE (CEIG-Certified). Date: 22 November 2024.",
        source_excerpt="HP Steam hydro test PASSED. Bureau Veritas BV-2024-BL-0471. CEIG-certified witness. 22 Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.high,
        timestamp=ago(3),
    )
    evidence_items.append(ev_d1)

    # --- SCENARIO E: act-032 — MCC Cabling (Verification Required — CEIG NCR contradiction) ---
    ev_e1 = EvidenceItem(
        id="ev-e1",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Electrical_Weekly_Report_Bellary_2024-11-15.pdf",
        extracted_content="MCC Room cabling installation status: 55% complete. Cable tray installation "
                          "in MCC Room complete. Main feeder cables pulled and terminated on MCC boards. "
                          "Motor control cables in progress. Subcontractor: Carrot Controls & Electrical.",
        source_excerpt="Electrical weekly report: MCC cabling 55% complete. 15 Nov 2024.",
        relation_type=RelationType.supports_progress_of,
        source_reliability_signal=SourceReliabilitySignal.medium,
        timestamp=ago(11),
    )
    ev_e2 = EvidenceItem(
        id="ev-e2",
        source_system="document_folder",
        ingesting_connector="document_folder_ingestor_v1",
        provenance_ref="Site_QC_Inspection_MCC_Bellary_2024-11-18.pdf",
        extracted_content="QC INSPECTION REPORT — MCC Room Cable Installation. Date: 18-Nov-2024. "
                          "Inspection finding: Motor control cables NOT terminated on 12 of 24 MCC boards "
                          "as claimed. Actual measured completion: 30–35%. "
                          "NCR raised: NCR-2024-E-041. Previous claim of 55% cannot be substantiated. "
                          "CEIG pre-inspection scheduled — current discrepancy must be resolved first.",
        source_excerpt="QC Inspection 18 Nov 2024: MCC cabling actually 30–35%, not 55%. NCR-2024-E-041 raised.",
        relation_type=RelationType.contradicts,
        source_reliability_signal=SourceReliabilitySignal.high,
        timestamp=ago(8),
    )
    evidence_items.extend([ev_e1, ev_e2])

    # --- Additional evidence for other activities ---
    ev_misc = [
        EvidenceItem(
            id="ev-m1", source_system="schedule_xer",
            ingesting_connector="schedule_xer_ingestor_v1",
            provenance_ref="Bellary_CCGT_P6_Export_2024-11-20.xer",
            extracted_content="TSK-001: Site Preparation and Clearing — Bellary CCGT site. Status: Complete. "
                              "Actual Finish: 15-Mar-2024. 100%.",
            source_excerpt="P6: Site preparation 100% complete, Mar 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=ago(7),
        ),
        EvidenceItem(
            id="ev-m2", source_system="document_folder",
            ingesting_connector="document_folder_ingestor_v1",
            provenance_ref="HRSG_Steel_Progress_Bellary_2024-11-10.pdf",
            extracted_content="HRSG Structural Steelwork Bay A — Bellary site: Column erection complete. "
                              "Primary beam connections 70% complete. Secondary steelwork ongoing. "
                              "OISD-STD-116 fireproofing VO approved — works incorporated. "
                              "Mango Civil Works on site.",
            source_excerpt="HRSG Bay A steelwork 70% complete. OISD fireproofing incorporated. Nov 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=ago(17),
        ),
        EvidenceItem(
            id="ev-m3", source_system="document_folder",
            ingesting_connector="document_folder_ingestor_v1",
            provenance_ref="Main_Transformer_FAT_Certificate_Bellary_2024-10-30.pdf",
            extracted_content="FACTORY ACCEPTANCE TEST CERTIFICATE — Main Power Transformer 900MVA 400/33kV. "
                              "Manufacturer: BHEL. All factory tests passed per IS 2026. "
                              "Certificate No. BHEL-2024-FAT-0872. Delivered to Bellary site 05-Nov-2024.",
            source_excerpt="Main transformer FAT passed per IS 2026. BHEL-2024-FAT-0872. Delivered 5 Nov 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.high,
            timestamp=ago(22),
        ),
        EvidenceItem(
            id="ev-m4", source_system="schedule_xer",
            ingesting_connector="schedule_xer_ingestor_v1",
            provenance_ref="Bellary_CCGT_P6_Export_2024-11-20.xer",
            extracted_content="TSK-030: Main Transformer Receipt and Inspection. Status: Complete. "
                              "Actual Finish: 07-Nov-2024.",
            source_excerpt="P6: Main transformer receipt 100% complete 7 Nov 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=ago(7),
        ),
        EvidenceItem(
            id="ev-m5", source_system="document_folder",
            ingesting_connector="document_folder_ingestor_v1",
            provenance_ref="DCS_Installation_Status_Bellary_2024-11-14.pdf",
            extracted_content="DCS Cabinet Installation — Bellary CCGT. Avocado Automation. "
                              "18 of 24 cabinets fully wired. Remaining 6 cabinets in progress. "
                              "FAT certificates received for DCS hardware. Estimated completion: 10-Dec-2024.",
            source_excerpt="DCS: 18/24 cabinets wired (60%). Avocado Automation. Nov 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=ago(13),
        ),
        EvidenceItem(
            id="ev-m6", source_system="document_folder",
            ingesting_connector="document_folder_ingestor_v1",
            provenance_ref="Pre_Comm_Civil_Checklist_Bellary_2024-11-20.pdf",
            extracted_content="Pre-Commissioning Checklist — Civil and Structural, Bellary CCGT. "
                              "Total items: 45. Completed: 36. Outstanding: 9 items (minor punchlist). "
                              "Estimated 80% complete. Signed off by: Site Manager R. Srinivasan, CEIG-Certified PE.",
            source_excerpt="Pre-comm civil 36/45 items complete (80%). Signed R. Srinivasan CEIG-PE. 20 Nov 2024.",
            relation_type=RelationType.supports_progress_of,
            source_reliability_signal=SourceReliabilitySignal.high,
            timestamp=ago(7),
        ),
        EvidenceItem(
            id="ev-m7", source_system="boq_upload",
            ingesting_connector="boq_ingestor_v1",
            provenance_ref="Bellary_CCGT_BOQ_Rev5.xlsx:row_42",
            extracted_content="BOQ Item 4.3: MCC Room Cable Installation | Qty: 1 Lot | "
                              "Rate: ₹2.35 Cr | Claimed to date: ₹1.29 Cr (55%) | Approved to date: ₹78.3 L (33%). "
                              "Discrepancy flagged. NCR-2024-E-041 open.",
            source_excerpt="BOQ: MCC cabling 55% claimed, only 33% approved (₹50.9 L discrepancy). NCR open.",
            relation_type=RelationType.contradicts,
            source_reliability_signal=SourceReliabilitySignal.medium,
            timestamp=ago(4),
        ),
    ]
    evidence_items.extend(ev_misc)

    session.add_all(evidence_items)
    session.flush()

    # -------------------------------------------------------------------------
    # LINK EVIDENCE ITEMS TO ACTIVITIES
    # -------------------------------------------------------------------------

    links = [
        {"activity_id": "act-010", "evidence_item_id": "ev-a1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-010", "evidence_item_id": "ev-a2", "relation_type": "supports_progress_of"},
        {"activity_id": "act-010", "evidence_item_id": "ev-a3", "relation_type": "supports_progress_of"},
        {"activity_id": "act-013", "evidence_item_id": "ev-b1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-013", "evidence_item_id": "ev-b2", "relation_type": "supports_progress_of"},
        {"activity_id": "act-013", "evidence_item_id": "ev-b3", "relation_type": "supports_progress_of"},
        {"activity_id": "act-003", "evidence_item_id": "ev-c1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-022", "evidence_item_id": "ev-d1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-032", "evidence_item_id": "ev-e1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-032", "evidence_item_id": "ev-e2", "relation_type": "contradicts"},
        {"activity_id": "act-032", "evidence_item_id": "ev-m7", "relation_type": "contradicts"},
        {"activity_id": "act-001", "evidence_item_id": "ev-m1", "relation_type": "supports_progress_of"},
        {"activity_id": "act-004", "evidence_item_id": "ev-m2", "relation_type": "supports_progress_of"},
        {"activity_id": "act-030", "evidence_item_id": "ev-m3", "relation_type": "supports_progress_of"},
        {"activity_id": "act-030", "evidence_item_id": "ev-m4", "relation_type": "supports_progress_of"},
        {"activity_id": "act-040", "evidence_item_id": "ev-m5", "relation_type": "supports_progress_of"},
        {"activity_id": "act-050", "evidence_item_id": "ev-m6", "relation_type": "supports_progress_of"},
    ]

    for link in links:
        session.execute(activity_evidence_items.insert().values(**link))

    # -------------------------------------------------------------------------
    # LINK ACTIVITIES TO MILESTONES
    # -------------------------------------------------------------------------

    milestone_links = [
        {"activity_id": "act-001", "milestone_id": "ms-001"},
        {"activity_id": "act-002", "milestone_id": "ms-001"},
        {"activity_id": "act-003", "milestone_id": "ms-001"},
        {"activity_id": "act-004", "milestone_id": "ms-001"},
        {"activity_id": "act-005", "milestone_id": "ms-001"},
        {"activity_id": "act-010", "milestone_id": "ms-002"},
        {"activity_id": "act-011", "milestone_id": "ms-002"},
        {"activity_id": "act-012", "milestone_id": "ms-002"},
        {"activity_id": "act-013", "milestone_id": "ms-002"},
        {"activity_id": "act-022", "milestone_id": "ms-003"},
        {"activity_id": "act-030", "milestone_id": "ms-004"},
        {"activity_id": "act-031", "milestone_id": "ms-004"},
        {"activity_id": "act-032", "milestone_id": "ms-004"},
        {"activity_id": "act-050", "milestone_id": "ms-005"},
        {"activity_id": "act-051", "milestone_id": "ms-005"},
        {"activity_id": "act-055", "milestone_id": "ms-006"},
    ]

    for link in milestone_links:
        session.execute(activity_milestones.insert().values(**link))

    session.execute(deliverable_evidence_items.insert().values(
        deliverable_id="del-001", evidence_item_id="ev-a1", relation_type="supports_progress_of",
    ))
    session.execute(deliverable_evidence_items.insert().values(
        deliverable_id="del-003", evidence_item_id="ev-m3", relation_type="supports_progress_of",
    ))

    session.commit()
    _seed_scores(session)

    print(f"  {len(all_activities)} activities seeded (Bellary CCGT)")
    print(f"  {len(milestones)} milestones seeded")
    print(f"  {len(deliverables)} deliverables seeded")
    print(f"  {len(evidence_items)} evidence items seeded")
    print(f"  {len(links)} evidence links created")
    print("Done.")


def _seed_scores(session):
    from app.agents.confidence_agent import compute_evidence_score

    activity_score_overrides = {
        "act-010": {
            "ev": 0.850, "conf": 0.850,
            "reasoning": "Three independent sources — official GE delivery inspection, transmittal record (TRS-2024-447), and P6 schedule — all corroborate 100% completion at Bellary site. Source reliability is high. Confidence closely matches Evidence Score.",
            "missing": None, "vr": False,
        },
        "act-013": {
            "ev": 0.800, "conf": 0.350,
            "reasoning": "Three sources agree on 60% progress, but all originate from Brinjal Mechanical Systems — a subcontractor with a documented history of overclaiming physical completion on this project. The P6 schedule entry is also Brinjal-sourced. An open TQ (TQ-2024-088) on IBR drum alignment tolerance adds further uncertainty. Independent CEIG or Client Representative verification is absent.",
            "missing": "Independent third-party site inspection or Bellary Power Ltd Client Representative walkdown to verify Brinjal Mechanical's 60% claim",
            "vr": False,
        },
        "act-003": {
            "ev": 0.200, "conf": 0.300,
            "reasoning": "Only one source — a four-week-old informal foreman verbal update. RFI-2024-047 on IS 2645 waterproofing spec is still open, which may affect pour completion certification. No drawing, inspection record, or schedule confirmation since October 2024.",
            "missing": "Recent site inspection record or concrete pour completion certificate (last update 28 days old). RFI-2024-047 resolution required before pour cert can be issued.",
            "vr": False,
        },
        "act-022": {
            "ev": 0.300, "conf": 0.750,
            "reasoning": "A single source, but it is a Bureau Veritas third-party witnessed hydrostatic test certificate with CEIG-certified Client Representative sign-off — the highest-reliability source type for this activity type. One authoritative certified record outweighs multiple informal updates.",
            "missing": None, "vr": False,
        },
        "act-032": {
            "ev": 0.500, "conf": 0.250,
            "reasoning": "CEIG pre-inspection QC report (NCR-2024-E-041) directly contradicts Carrot Controls & Electrical's progress claim. BOQ approval rate (33%) also contradicts the 55% claim. CEIG-raised NCR means this activity cannot be reported until resolved. Verified completion is 30–35%, not 55%.",
            "missing": "Resolution of NCR-2024-E-041 and independent CEIG re-measurement of MCC cabling completion before next progress claim can be accepted.",
            "vr": True,
        },
    }

    for activity_id, scores in activity_score_overrides.items():
        activity = session.get(Activity, activity_id)
        if activity:
            activity.evidence_score = scores["ev"]
            activity.confidence_score = scores["conf"]
            activity.confidence_reasoning = scores["reasoning"]
            activity.missing_evidence = scores["missing"]
            activity.verification_required = scores["vr"]
            session.add(activity)

    all_activities = session.query(Activity).all()
    for activity in all_activities:
        if activity.id not in activity_score_overrides:
            ev_score = compute_evidence_score(activity.evidence_items)
            activity.evidence_score = ev_score
            activity.confidence_score = round(ev_score * 0.75, 3)
            activity.verification_required = ev_score < 0.25 and activity.confidence_score < 0.30
            session.add(activity)

    session.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        clear_existing(session)
        seed(session)
    finally:
        session.close()
