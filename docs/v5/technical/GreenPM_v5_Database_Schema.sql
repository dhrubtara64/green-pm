-- =============================================================================
-- Green PM v5 Database Schema
-- PostgreSQL 15+
-- Generated: 2026-08-03
-- Total: 56+ tables, 65+ ENUMs, 135+ indexes
-- Engineering Project Intelligence Platform
-- All tables use Row Level Security (RLS) with tenant isolation.
-- Table order respects FK dependencies; all inline FK refs resolve forward-safe.
-- Circular FK (decisions <-> decision_options) resolved via ALTER TABLE post-creation.
-- =============================================================================

BEGIN;
SET client_min_messages = WARNING;

-- ---------------------------------------------------------------------------
-- Auto-update timestamp trigger (applied to all tables with updated_at)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- SECTION 1: ENUMS — CORE PLATFORM
-- =============================================================================

CREATE TYPE tenant_plan AS ENUM ('pilot', 'professional', 'enterprise');

CREATE TYPE user_role AS ENUM (
    'super_admin', 'tenant_admin', 'project_manager',
    'engineer', 'vendor_portal', 'executive', 'viewer'
);

CREATE TYPE project_status AS ENUM ('setup', 'active', 'on_hold', 'completed', 'archived');

CREATE TYPE project_phase  AS ENUM (
    'engineering', 'procurement', 'construction', 'commissioning', 'cod'
);

-- =============================================================================
-- SECTION 2: ENUMS — SCHEDULE / ACTIVITY
-- =============================================================================

CREATE TYPE activity_status AS ENUM (
    'not_started', 'in_progress', 'completed', 'delayed', 'on_hold', 'cancelled'
);

CREATE TYPE activity_type AS ENUM (
    'engineering', 'procurement', 'construction',
    'inspection', 'commissioning', 'administrative'
);

CREATE TYPE dependency_type AS ENUM ('fs', 'ss', 'ff', 'sf');
-- fs = Finish-to-Start, ss = Start-to-Start, ff = Finish-to-Finish, sf = Start-to-Finish

CREATE TYPE milestone_status AS ENUM ('upcoming', 'achieved', 'missed', 'at_risk');

-- =============================================================================
-- SECTION 3: ENUMS — EVIDENCE
-- =============================================================================

CREATE TYPE capture_type AS ENUM (
    'site_photo', 'site_video', 'voice_memo', 'document_upload',
    'qr_scan', 'form_submission', 'iot_sensor', 'drone_image',
    'surveyor_report', 'inspection_report', 'weather_log', 'financial_document'
);

CREATE TYPE evidence_status AS ENUM (
    'draft', 'submitted', 'under_review', 'approved', 'rejected', 'archived'
);

CREATE TYPE evidence_review_outcome AS ENUM ('approved', 'rejected', 'needs_revision');

CREATE TYPE reliability_tier AS ENUM ('primary', 'secondary', 'tertiary');
-- primary = surveyor/inspector; secondary = PM/engineer; tertiary = unverified field input

-- =============================================================================
-- SECTION 4: ENUMS — DRAWING / DOCUMENT
-- =============================================================================

CREATE TYPE drawing_type AS ENUM (
    'GA', 'detail', 'P_and_ID', 'electrical',
    'structural', 'civil', 'architectural', 'vendor'
);

CREATE TYPE drawing_status AS ENUM (
    'draft', 'IFA', 'IFC', 'AFC', 'superseded', 'cancelled'
);
-- IFA = Issued For Approval, IFC = Issued For Construction, AFC = Approved For Construction

CREATE TYPE revision_type AS ENUM (
    'issued_for_approval', 'issued_for_construction',
    'issued_for_information', 'as_built'
);

CREATE TYPE rfi_status AS ENUM ('open', 'responded', 'closed', 'cancelled');

CREATE TYPE document_type AS ENUM (
    'specification', 'report', 'correspondence', 'contract',
    'method_statement', 'risk_assessment', 'quality_plan'
);

-- =============================================================================
-- SECTION 5: ENUMS — CHANGE
-- =============================================================================

CREATE TYPE change_type AS ENUM (
    'scope_change', 'design_change', 'vendor_change', 'site_condition',
    'client_instruction', 'regulatory', 'value_engineering'
);

CREATE TYPE change_status AS ENUM (
    'draft', 'submitted', 'under_impact_assessment', 'pending_approval',
    'approved', 'rejected', 'implemented', 'cancelled'
);

CREATE TYPE change_approval_status AS ENUM ('pending', 'approved', 'rejected', 'delegated');

-- =============================================================================
-- SECTION 6: ENUMS — EQUIPMENT
-- =============================================================================

CREATE TYPE equipment_status AS ENUM (
    'on_order', 'manufacturing', 'fat_pending', 'fat_complete',
    'dispatched', 'in_transit', 'received', 'stored', 'installed', 'commissioned'
);
-- fat = Factory Acceptance Test

CREATE TYPE inspection_type AS ENUM (
    'dimensional', 'hydrostatic', 'radiographic', 'ultrasonic',
    'visual', 'performance', 'receiving'
);

CREATE TYPE inspection_status AS ENUM (
    'scheduled', 'in_progress', 'passed', 'failed', 'conditionally_passed', 'waived'
);

-- =============================================================================
-- SECTION 7: ENUMS — VENDOR / SUPPLY CHAIN
-- =============================================================================

CREATE TYPE vendor_status   AS ENUM (
    'approved', 'conditional', 'suspended', 'blacklisted', 'under_review'
);

CREATE TYPE po_status AS ENUM (
    'draft', 'issued', 'acknowledged', 'partially_delivered',
    'fully_delivered', 'closed', 'cancelled'
);

CREATE TYPE dispatch_status AS ENUM ('pending', 'in_progress', 'completed', 'delayed', 'cancelled');

-- 10-stage dispatch lifecycle (Supply Chain Intelligence Engine)
CREATE TYPE dispatch_stage AS ENUM (
    'manufacturing', 'fat', 'packaging', 'clearance', 'loading',
    'in_transit', 'port_of_arrival', 'customs', 'inland_transit', 'site_receipt'
);

CREATE TYPE shipment_status AS ENUM (
    'planned', 'departed', 'in_transit', 'arrived', 'cleared', 'delivered'
);

CREATE TYPE package_type AS ENUM (
    'bulk_material', 'tagged_equipment', 'instrument', 'electrical',
    'piping', 'structural', 'civil'
);

-- =============================================================================
-- SECTION 8: ENUMS — RISK
-- =============================================================================

CREATE TYPE risk_category AS ENUM (
    'technical', 'schedule', 'cost', 'safety', 'quality',
    'regulatory', 'vendor', 'weather', 'force_majeure', 'contractual'
);

CREATE TYPE risk_status AS ENUM (
    'identified', 'assessed', 'mitigation_in_progress',
    'mitigated', 'accepted', 'closed', 'materialized'
);

CREATE TYPE probability_level AS ENUM ('very_low', 'low', 'medium', 'high', 'very_high');

CREATE TYPE impact_level AS ENUM ('negligible', 'minor', 'moderate', 'major', 'critical');

CREATE TYPE mitigation_status AS ENUM (
    'planned', 'in_progress', 'completed', 'deferred', 'cancelled'
);

-- =============================================================================
-- SECTION 9: ENUMS — DECISION (10-state lifecycle)
-- =============================================================================

CREATE TYPE decision_status AS ENUM (
    'draft', 'options_defined', 'under_review', 'pending_approval', 'approved',
    'rejected', 'implemented', 'closed', 'deferred', 'escalated'
);

CREATE TYPE decision_type AS ENUM (
    'technical', 'commercial', 'schedule', 'resource',
    'safety', 'regulatory', 'vendor', 'scope'
);

CREATE TYPE approval_workflow_status AS ENUM (
    'not_started', 'in_progress', 'approved', 'rejected', 'escalated'
);

-- =============================================================================
-- SECTION 10: ENUMS — COORDINATION (new v5)
-- =============================================================================

-- Pipeline: Event → Impact → Action → Notify → Acknowledge → Execute → Verify → Close
CREATE TYPE coordination_status AS ENUM (
    'pending', 'acknowledged', 'executing', 'verifying', 'closed', 'overdue', 'cancelled'
);

CREATE TYPE coordination_closure_type AS ENUM (
    'completed', 'cancelled', 'delegated', 'superseded', 'not_required'
);

-- =============================================================================
-- SECTION 11: ENUMS — READINESS (new v5)
-- =============================================================================

CREATE TYPE readiness_gate_type AS ENUM (
    'engineering',   -- All IFC drawings issued; all specifications approved
    'material',      -- All materials on site; all inspections passed
    'construction',  -- All prerequisites met; permits in place
    'quality',       -- QA/QC protocols in place; inspection plans approved
    'commissioning', -- All systems complete; punch lists cleared
    'cod'            -- All handover documents signed; regulatory clearances obtained
);

CREATE TYPE readiness_gate_status AS ENUM (
    'not_started', 'in_progress', 'blocked', 'conditionally_ready', 'ready'
);

CREATE TYPE readiness_criteria_status AS ENUM (
    'not_checked', 'passed', 'failed', 'waived', 'not_applicable'
);

-- =============================================================================
-- SECTION 12: ENUMS — SIMULATION (new v5)
-- =============================================================================

CREATE TYPE simulation_status AS ENUM ('draft', 'queued', 'running', 'completed', 'failed');

CREATE TYPE simulation_output_type AS ENUM (
    'schedule_impact', 'cost_impact', 'critical_path', 'risk_exposure', 'recommendations'
);

CREATE TYPE perturbation_type AS ENUM (
    'delay', 'resource_change', 'scope_change', 'cost_change', 'removal', 'addition'
);

-- =============================================================================
-- SECTION 13: ENUMS — ORGANIZATIONAL MEMORY (new v5)
-- =============================================================================

CREATE TYPE memory_record_type AS ENUM (
    'decision_outcome', 'vendor_pattern', 'risk_pattern', 'recovery_strategy',
    'change_profile', 'schedule_recovery', 'cost_overrun_pattern'
);

CREATE TYPE memory_category AS ENUM ('positive', 'negative', 'neutral', 'mixed');

-- =============================================================================
-- SECTION 14: ENUMS — PROJECT INTELLIGENCE GRAPH (new v5)
-- =============================================================================

-- 22 node entity types covering all major project entities
CREATE TYPE graph_node_entity_type AS ENUM (
    'activity', 'milestone', 'drawing', 'document', 'equipment', 'vendor',
    'dispatch', 'evidence', 'change', 'decision', 'risk', 'issue', 'gate',
    'wbs', 'package', 'shipment', 'claim', 'payment', 'inspection',
    'commissioning_item', 'organizational_unit', 'person'
);

-- 30 typed directional edge types
CREATE TYPE graph_edge_type AS ENUM (
    'blocks', 'supplies_to', 'approved_by', 'impacts', 'depends_on',
    'supersedes', 'conflicts_with', 'delivers_for', 'reviews', 'assigned_to',
    'coordinates_with', 'escalates_to', 'preceded_by', 'parallel_with',
    'requires', 'satisfies', 'verifies', 'closes', 'monitors', 'triggers',
    'owns', 'raised_by', 'resolved_by', 'references', 'superseded_by',
    'mitigates', 'raises_risk_to', 'clears', 'gates', 'reports_to'
);

-- =============================================================================
-- SECTION 15: ENUMS — SUPPORTING / REPORTING
-- =============================================================================

CREATE TYPE notification_type   AS ENUM ('email', 'in_app', 'webhook');

CREATE TYPE notification_status AS ENUM (
    'pending', 'sent', 'delivered', 'failed', 'suppressed'
);

CREATE TYPE report_type AS ENUM (
    'weekly_progress', 'monthly_executive', 'milestone_report', 'vendor_performance',
    'change_log', 'risk_register', 'forecast_summary', 'executive_digital_twin'
);

CREATE TYPE forecast_domain AS ENUM (
    'schedule', 'budget', 'quality', 'resource', 'commissioning', 'cashflow'
);

CREATE TYPE alignment_gap_status     AS ENUM ('open', 'acknowledged', 'resolved', 'escalated');

CREATE TYPE contradiction_severity   AS ENUM ('low', 'medium', 'high', 'critical');

CREATE TYPE outbox_status            AS ENUM ('pending', 'published', 'failed');

-- =============================================================================
-- SECTION 16: CORE PLATFORM TABLES
-- Dependency order: tenants → users/projects → user_project_access
-- =============================================================================

CREATE TABLE tenants (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL,
    plan        tenant_plan NOT NULL DEFAULT 'pilot',
    domain      text,
    settings    jsonb       NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT NOW(),
    updated_at  timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN tenants.settings IS 'Tenant-level config: feature flags, branding, notification preferences, API limits';

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE projects (
    id          uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        text            NOT NULL,
    code        text            NOT NULL,
    description text,
    status      project_status  NOT NULL DEFAULT 'setup',
    phase       project_phase   NOT NULL DEFAULT 'engineering',
    start_date  date,
    end_date    date,
    settings    jsonb           NOT NULL DEFAULT '{}',
    created_at  timestamptz     NOT NULL DEFAULT NOW(),
    updated_at  timestamptz     NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)
);

COMMENT ON COLUMN projects.settings IS 'Project-level settings: reporting cadence, readiness gate config, simulation parameters';

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE users (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           text        NOT NULL,
    full_name       text        NOT NULL,
    role            user_role   NOT NULL DEFAULT 'viewer',
    is_active       boolean     NOT NULL DEFAULT true,
    last_login_at   timestamptz,
    created_at      timestamptz NOT NULL DEFAULT NOW(),
    updated_at      timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, email)
);

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE user_project_access (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id  uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role        user_role   NOT NULL DEFAULT 'viewer',
    granted_by  uuid        NOT NULL REFERENCES users(id),
    granted_at  timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, project_id)
);

-- =============================================================================
-- SECTION 17: VENDOR TABLES (defined before purchase_orders and equipment_items)
-- =============================================================================

CREATE TABLE vendors (
    id                  uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                text            NOT NULL,
    code                text,
    status              vendor_status   NOT NULL DEFAULT 'under_review',
    contact_email       text,
    contact_name        text,
    country             text,
    registration_number text,
    approved_at         date,
    approved_by         uuid            REFERENCES users(id) ON DELETE SET NULL,
    created_at          timestamptz     NOT NULL DEFAULT NOW(),
    updated_at          timestamptz     NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)
);

CREATE TRIGGER trg_vendors_updated_at
    BEFORE UPDATE ON vendors FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SECTION 18: SCHEDULE TABLES
-- =============================================================================

CREATE TABLE wbs_elements (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id   uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code        text        NOT NULL,
    name        text        NOT NULL,
    level       integer     NOT NULL DEFAULT 1,
    parent_id   uuid        REFERENCES wbs_elements(id) ON DELETE SET NULL,
    sort_order  integer     NOT NULL DEFAULT 0,
    created_at  timestamptz NOT NULL DEFAULT NOW(),
    updated_at  timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, code)
);

COMMENT ON COLUMN wbs_elements.level IS 'Hierarchy level: 1=top-level, 2=sub-level, etc.';

CREATE TRIGGER trg_wbs_elements_updated_at
    BEFORE UPDATE ON wbs_elements FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE activities (
    id                  uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    wbs_id              uuid            REFERENCES wbs_elements(id) ON DELETE SET NULL,
    name                text            NOT NULL,
    description         text,
    status              activity_status NOT NULL DEFAULT 'not_started',
    type                activity_type   NOT NULL DEFAULT 'construction',
    planned_start       date,
    planned_finish      date,
    actual_start        date,
    actual_finish       date,
    progress_pct        numeric(5,2)    NOT NULL DEFAULT 0
                            CHECK (progress_pct >= 0 AND progress_pct <= 100),
    float_days          integer         NOT NULL DEFAULT 0,
    is_critical         boolean         NOT NULL DEFAULT false,
    responsible_user_id uuid            REFERENCES users(id) ON DELETE SET NULL,
    duration_days       integer,
    planned_cost        numeric(15,2),
    actual_cost         numeric(15,2),
    created_at          timestamptz     NOT NULL DEFAULT NOW(),
    updated_at          timestamptz     NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN activities.float_days  IS 'Total float in days; 0 = on critical path';
COMMENT ON COLUMN activities.is_critical IS 'True when float_days = 0 and activity drives project end date';

CREATE TRIGGER trg_activities_updated_at
    BEFORE UPDATE ON activities FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE milestones (
    id                  uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid                NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid                NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    activity_id         uuid                REFERENCES activities(id) ON DELETE SET NULL,
    name                text                NOT NULL,
    planned_date        date                NOT NULL,
    actual_date         date,
    status              milestone_status    NOT NULL DEFAULT 'upcoming',
    responsible_user_id uuid                REFERENCES users(id) ON DELETE SET NULL,
    created_at          timestamptz         NOT NULL DEFAULT NOW(),
    updated_at          timestamptz         NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_milestones_updated_at
    BEFORE UPDATE ON milestones FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE activity_dependencies (
    id              uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    predecessor_id  uuid            NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    successor_id    uuid            NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    dependency_type dependency_type NOT NULL DEFAULT 'fs',
    lag_days        integer         NOT NULL DEFAULT 0,
    created_at      timestamptz     NOT NULL DEFAULT NOW(),
    UNIQUE (predecessor_id, successor_id)
);

-- =============================================================================
-- SECTION 19: EVIDENCE TABLES
-- Defined before dispatch_stages (which references evidences)
-- =============================================================================

CREATE TABLE evidences (
    id               uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       uuid             NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id        uuid             NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type      text             NOT NULL,
    entity_id        uuid             NOT NULL,
    capture_type     capture_type     NOT NULL,
    status           evidence_status  NOT NULL DEFAULT 'draft',
    captured_by      uuid             REFERENCES users(id) ON DELETE SET NULL,
    captured_at      timestamptz      NOT NULL DEFAULT NOW(),
    file_ref         text,
    description      text,
    location_lat     numeric(9,6),
    location_lng     numeric(9,6),
    gcp_bucket       text,
    gcp_object       text,
    reliability_tier reliability_tier NOT NULL DEFAULT 'secondary',
    confidence_score numeric(3,2)     CHECK (confidence_score >= 0 AND confidence_score <= 1),
    metadata         jsonb            NOT NULL DEFAULT '{}',
    created_at       timestamptz      NOT NULL DEFAULT NOW(),
    updated_at       timestamptz      NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN evidences.entity_type      IS 'Polymorphic: activity, drawing, equipment, vendor, dispatch, etc.';
COMMENT ON COLUMN evidences.entity_id        IS 'UUID of the referenced entity matching entity_type';
COMMENT ON COLUMN evidences.reliability_tier IS 'primary=surveyor/inspector; secondary=PM/engineer; tertiary=unverified';
COMMENT ON COLUMN evidences.confidence_score IS 'Pre-computed Evidence Score v5 component (0.00–1.00)';
COMMENT ON COLUMN evidences.gcp_object       IS 'GCS object path; gcp_bucket is the bucket name';

CREATE TRIGGER trg_evidences_updated_at
    BEFORE UPDATE ON evidences FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE evidence_reviews (
    id                 uuid                    PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id        uuid                    NOT NULL REFERENCES evidences(id) ON DELETE CASCADE,
    reviewer_id        uuid                    NOT NULL REFERENCES users(id),
    outcome            evidence_review_outcome NOT NULL,
    comments           text,
    reviewed_at        timestamptz             NOT NULL DEFAULT NOW(),
    reliability_weight numeric(3,2)            NOT NULL DEFAULT 1.0
                           CHECK (reliability_weight >= 0 AND reliability_weight <= 1),
    created_at         timestamptz             NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN evidence_reviews.reliability_weight IS 'Weight for Evidence Score corroboration_ratio calculation';

-- ---------------------------------------------------------------------------

CREATE TABLE evidence_scores (
    id                     uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id             uuid         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id              uuid         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type            text         NOT NULL,
    entity_id              uuid         NOT NULL,
    -- Evidence Score v5 formula:
    -- score = (source_count/10 × 0.25) + (recency_decay × 0.25)
    --       + (corroboration_ratio × 0.25) + (capture_diversity × 0.15)
    --       + (reliability_weight_avg × 0.10)
    score_value            numeric(4,3) NOT NULL DEFAULT 0,
    source_count           integer      NOT NULL DEFAULT 0,
    recency_decay          numeric(4,3) NOT NULL DEFAULT 0,
    corroboration_ratio    numeric(4,3) NOT NULL DEFAULT 0,
    capture_diversity      numeric(4,3) NOT NULL DEFAULT 0,
    reliability_weight_avg numeric(4,3) NOT NULL DEFAULT 0,
    computed_at            timestamptz  NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, entity_type, entity_id)
);

COMMENT ON COLUMN evidence_scores.score_value   IS 'Composite Evidence Score v5 (0.000 to 1.000)';
COMMENT ON COLUMN evidence_scores.recency_decay IS 'Time-decayed weight; evidence >30d old scores lower';

-- =============================================================================
-- SECTION 20: DRAWING / DOCUMENT TABLES
-- =============================================================================

CREATE TABLE drawings (
    id                  uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    drawing_number      text            NOT NULL,
    title               text            NOT NULL,
    type                drawing_type    NOT NULL,
    discipline          text,
    current_revision    text,
    current_status      drawing_status  NOT NULL DEFAULT 'draft',
    responsible_user_id uuid            REFERENCES users(id) ON DELETE SET NULL,
    created_at          timestamptz     NOT NULL DEFAULT NOW(),
    updated_at          timestamptz     NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, drawing_number)
);

CREATE TRIGGER trg_drawings_updated_at
    BEFORE UPDATE ON drawings FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE drawing_revisions (
    id                  uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id          uuid            NOT NULL REFERENCES drawings(id) ON DELETE CASCADE,
    project_id          uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    revision            text            NOT NULL,
    revision_type       revision_type   NOT NULL,
    status              drawing_status  NOT NULL DEFAULT 'draft',
    issued_at           date,
    issued_by           uuid            REFERENCES users(id) ON DELETE SET NULL,
    file_ref            text,
    gcp_object          text,
    supersedes_revision text,
    is_current          boolean         NOT NULL DEFAULT false,
    created_at          timestamptz     NOT NULL DEFAULT NOW(),
    UNIQUE (drawing_id, revision)
);

COMMENT ON COLUMN drawing_revisions.is_current          IS 'Only one revision per drawing should be true; enforced at application layer';
COMMENT ON COLUMN drawing_revisions.supersedes_revision IS 'Revision identifier this revision supersedes';

-- ---------------------------------------------------------------------------

CREATE TABLE rfis (
    id           uuid       PRIMARY KEY DEFAULT gen_random_uuid(),
    drawing_id   uuid       REFERENCES drawings(id) ON DELETE SET NULL,
    project_id   uuid       NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id    uuid       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rfi_number   text       NOT NULL,
    subject      text       NOT NULL,
    description  text,
    status       rfi_status NOT NULL DEFAULT 'open',
    raised_by    uuid       REFERENCES users(id) ON DELETE SET NULL,
    raised_at    date       NOT NULL DEFAULT CURRENT_DATE,
    responded_by uuid       REFERENCES users(id) ON DELETE SET NULL,
    responded_at date,
    response     text,
    created_at   timestamptz NOT NULL DEFAULT NOW(),
    updated_at   timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, rfi_number)
);

CREATE TRIGGER trg_rfis_updated_at
    BEFORE UPDATE ON rfis FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE documents (
    id          uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id   uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type        document_type   NOT NULL,
    title       text            NOT NULL,
    revision    text,
    status      text            NOT NULL DEFAULT 'draft',
    file_ref    text,
    gcp_object  text,
    uploaded_by uuid            REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at timestamptz     NOT NULL DEFAULT NOW(),
    created_at  timestamptz     NOT NULL DEFAULT NOW(),
    updated_at  timestamptz     NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SECTION 21: CHANGE TABLES
-- =============================================================================

CREATE TABLE changes (
    id                uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid          NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id         uuid          NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    change_number     text          NOT NULL,
    type              change_type   NOT NULL,
    status            change_status NOT NULL DEFAULT 'draft',
    title             text          NOT NULL,
    description       text,
    originating_event text,
    requestor_id      uuid          REFERENCES users(id) ON DELETE SET NULL,
    submitted_at      timestamptz,
    implemented_at    timestamptz,
    created_at        timestamptz   NOT NULL DEFAULT NOW(),
    updated_at        timestamptz   NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, change_number)
);

COMMENT ON COLUMN changes.originating_event IS 'Human-readable description of triggering event';

CREATE TRIGGER trg_changes_updated_at
    BEFORE UPDATE ON changes FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE change_impacts (
    id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    change_id            uuid        NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    project_id           uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scope_impact         text,
    schedule_impact_days integer     NOT NULL DEFAULT 0,
    cost_impact          numeric(15,2) NOT NULL DEFAULT 0,
    quality_impact       text,
    safety_impact        text,
    affected_entities    jsonb       NOT NULL DEFAULT '[]',
    impact_score         numeric(4,2),
    assessed_by          uuid        REFERENCES users(id) ON DELETE SET NULL,
    assessed_at          timestamptz,
    created_at           timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN change_impacts.affected_entities IS 'Array of {entity_type, entity_id, description} from PIG traversal';
COMMENT ON COLUMN change_impacts.impact_score      IS 'Composite 0–10 score from Impact Analysis Engine';

-- ---------------------------------------------------------------------------

CREATE TABLE change_approvals (
    id             uuid                   PRIMARY KEY DEFAULT gen_random_uuid(),
    change_id      uuid                   NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    project_id     uuid                   NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    approver_id    uuid                   NOT NULL REFERENCES users(id),
    sequence_order integer                NOT NULL DEFAULT 1,
    status         change_approval_status NOT NULL DEFAULT 'pending',
    decision_at    timestamptz,
    comments       text,
    created_at     timestamptz            NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 22: SUPPLY CHAIN TABLES
-- Order: purchase_orders → dispatches → dispatch_stages → material_packages
--        → material_items → shipments → vendor_scores → equipment_items → equipment_inspections
-- =============================================================================

CREATE TABLE purchase_orders (
    id                uuid      PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id         uuid      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vendor_id         uuid      NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    po_number         text      NOT NULL,
    status            po_status NOT NULL DEFAULT 'draft',
    value             numeric(15,2),
    currency          text      NOT NULL DEFAULT 'USD',
    issued_at         date,
    delivery_due_date date,
    created_at        timestamptz NOT NULL DEFAULT NOW(),
    updated_at        timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, po_number)
);

CREATE TRIGGER trg_purchase_orders_updated_at
    BEFORE UPDATE ON purchase_orders FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE dispatches (
    id                    uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
    po_id                 uuid             NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    project_id            uuid             NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id             uuid             NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    vendor_id             uuid             NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    status                dispatch_status  NOT NULL DEFAULT 'pending',
    planned_dispatch_date date,
    actual_dispatch_date  date,
    planned_delivery_date date,
    actual_delivery_date  date,
    current_stage         dispatch_stage   NOT NULL DEFAULT 'manufacturing',
    description           text,
    created_at            timestamptz      NOT NULL DEFAULT NOW(),
    updated_at            timestamptz      NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_dispatches_updated_at
    BEFORE UPDATE ON dispatches FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE dispatch_stages (
    id           uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_id  uuid           NOT NULL REFERENCES dispatches(id) ON DELETE CASCADE,
    project_id   uuid           NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage        dispatch_stage NOT NULL,
    status       text           NOT NULL DEFAULT 'pending',
    started_at   timestamptz,
    completed_at timestamptz,
    notes        text,
    evidence_id  uuid           REFERENCES evidences(id) ON DELETE SET NULL,
    created_by   uuid           REFERENCES users(id) ON DELETE SET NULL,
    created_at   timestamptz    NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN dispatch_stages.status IS 'pending | in_progress | completed | skipped';

-- ---------------------------------------------------------------------------

CREATE TABLE material_packages (
    id              uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id       uuid         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    po_id           uuid         REFERENCES purchase_orders(id) ON DELETE SET NULL,
    vendor_id       uuid         REFERENCES vendors(id) ON DELETE SET NULL,
    package_number  text         NOT NULL,
    type            package_type NOT NULL,
    status          text         NOT NULL DEFAULT 'draft',
    mto_ref         text,
    readiness_score numeric(4,2),
    created_at      timestamptz  NOT NULL DEFAULT NOW(),
    updated_at      timestamptz  NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, package_number)
);

COMMENT ON COLUMN material_packages.mto_ref         IS 'Material Take-Off reference document';
COMMENT ON COLUMN material_packages.readiness_score IS '0–10 score from Supply Chain Intelligence Engine';

CREATE TRIGGER trg_material_packages_updated_at
    BEFORE UPDATE ON material_packages FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE material_items (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id   uuid        NOT NULL REFERENCES material_packages(id) ON DELETE CASCADE,
    project_id   uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id    uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    description  text        NOT NULL,
    tag_number   text,
    quantity     numeric(10,3) NOT NULL DEFAULT 0,
    unit         text        NOT NULL DEFAULT 'EA',
    dispatch_id  uuid        REFERENCES dispatches(id) ON DELETE SET NULL,
    received_qty numeric(10,3) NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT NOW(),
    updated_at   timestamptz NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_material_items_updated_at
    BEFORE UPDATE ON material_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE shipments (
    id                 uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    dispatch_id        uuid            NOT NULL REFERENCES dispatches(id) ON DELETE CASCADE,
    project_id         uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id          uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bl_number          text,
    vessel_name        text,
    port_of_loading    text,
    port_of_discharge  text,
    etd                date,
    eta                date,
    ata                date,
    status             shipment_status NOT NULL DEFAULT 'planned',
    created_at         timestamptz     NOT NULL DEFAULT NOW(),
    updated_at         timestamptz     NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN shipments.bl_number IS 'Bill of Lading number';
COMMENT ON COLUMN shipments.ata       IS 'Actual Time of Arrival at port of discharge';

CREATE TRIGGER trg_shipments_updated_at
    BEFORE UPDATE ON shipments FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE vendor_scores (
    id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id            uuid        NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    project_id           uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id            uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    overall_score        numeric(4,2) NOT NULL DEFAULT 0 CHECK (overall_score   BETWEEN 0 AND 10),
    quality_score        numeric(4,2) NOT NULL DEFAULT 0 CHECK (quality_score   BETWEEN 0 AND 10),
    delivery_score       numeric(4,2) NOT NULL DEFAULT 0 CHECK (delivery_score  BETWEEN 0 AND 10),
    responsiveness_score numeric(4,2) NOT NULL DEFAULT 0 CHECK (responsiveness_score BETWEEN 0 AND 10),
    documentation_score  numeric(4,2) NOT NULL DEFAULT 0 CHECK (documentation_score BETWEEN 0 AND 10),
    commercial_score     numeric(4,2) NOT NULL DEFAULT 0 CHECK (commercial_score BETWEEN 0 AND 10),
    relationship_score   numeric(4,2) NOT NULL DEFAULT 0 CHECK (relationship_score  BETWEEN 0 AND 10),
    computed_at          timestamptz  NOT NULL DEFAULT NOW(),
    event_trigger        text,
    created_at           timestamptz  NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN vendor_scores.overall_score  IS 'Weighted composite of 6 dimension scores (0–10)';
COMMENT ON COLUMN vendor_scores.event_trigger  IS 'Event that triggered recompute (e.g., delivery_late, ncr_raised)';

-- ---------------------------------------------------------------------------

CREATE TABLE equipment_items (
    id                uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        uuid             NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id         uuid             NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tag_number        text             NOT NULL,
    name              text             NOT NULL,
    description       text,
    status            equipment_status NOT NULL DEFAULT 'on_order',
    vendor_id         uuid             REFERENCES vendors(id) ON DELETE SET NULL,
    po_id             uuid             REFERENCES purchase_orders(id) ON DELETE SET NULL,
    activity_id       uuid             REFERENCES activities(id) ON DELETE SET NULL,
    specification_ref text,
    design_weight_kg  numeric(10,2),
    actual_weight_kg  numeric(10,2),
    is_tagged         boolean          NOT NULL DEFAULT true,
    created_at        timestamptz      NOT NULL DEFAULT NOW(),
    updated_at        timestamptz      NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, tag_number)
);

COMMENT ON COLUMN equipment_items.tag_number IS 'Unique equipment tag per project (e.g., P-101, V-201)';
COMMENT ON COLUMN equipment_items.is_tagged  IS 'true = individual tagged item; false = bulk untagged material';

CREATE TRIGGER trg_equipment_items_updated_at
    BEFORE UPDATE ON equipment_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE equipment_inspections (
    id             uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
    equipment_id   uuid              NOT NULL REFERENCES equipment_items(id) ON DELETE CASCADE,
    project_id     uuid              NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id      uuid              NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type           inspection_type   NOT NULL,
    status         inspection_status NOT NULL DEFAULT 'scheduled',
    scheduled_date date,
    actual_date    date,
    inspector_id   uuid              REFERENCES users(id) ON DELETE SET NULL,
    inspector_name text,
    result         text,
    ncr_ref        text,
    created_at     timestamptz       NOT NULL DEFAULT NOW(),
    updated_at     timestamptz       NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN equipment_inspections.ncr_ref IS 'Non-Conformance Report reference if inspection failed';

CREATE TRIGGER trg_equipment_inspections_updated_at
    BEFORE UPDATE ON equipment_inspections FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SECTION 23: ORGANIZATIONAL MEMORY TABLES
-- Defined before risks (which references memory_patterns)
-- =============================================================================

CREATE TABLE memory_patterns (
    id                  uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           uuid                NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    pattern_name        text                NOT NULL,
    pattern_type        memory_record_type  NOT NULL,
    trigger_conditions  jsonb               NOT NULL DEFAULT '{}',
    historical_outcomes jsonb               NOT NULL DEFAULT '[]',
    recommended_actions jsonb               NOT NULL DEFAULT '[]',
    confidence_score    numeric(3,2)        NOT NULL DEFAULT 0.5
                            CHECK (confidence_score >= 0 AND confidence_score <= 1),
    occurrence_count    integer             NOT NULL DEFAULT 1,
    last_matched_at     timestamptz,
    created_at          timestamptz         NOT NULL DEFAULT NOW(),
    updated_at          timestamptz         NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN memory_patterns.trigger_conditions  IS 'Conditions that activate this pattern (jsonb rule object)';
COMMENT ON COLUMN memory_patterns.historical_outcomes IS 'Array of {project_id, outcome, delta_days, delta_cost} from past matches';
COMMENT ON COLUMN memory_patterns.recommended_actions IS 'Array of recommended action strings for Decision and Risk engines';

CREATE TRIGGER trg_memory_patterns_updated_at
    BEFORE UPDATE ON memory_patterns FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SECTION 24: RISK TABLES
-- =============================================================================

CREATE TABLE risks (
    id                      uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              uuid              NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id               uuid              NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    risk_code               text,
    category                risk_category     NOT NULL,
    status                  risk_status       NOT NULL DEFAULT 'identified',
    title                   text              NOT NULL,
    description             text,
    probability             probability_level NOT NULL DEFAULT 'medium',
    impact                  impact_level      NOT NULL DEFAULT 'moderate',
    severity_score          numeric(4,2),
    owner_id                uuid              REFERENCES users(id) ON DELETE SET NULL,
    identified_at           date              NOT NULL DEFAULT CURRENT_DATE,
    target_resolution_date  date,
    monte_carlo_p50_days    integer,
    monte_carlo_p80_days    integer,
    monte_carlo_p50_cost    numeric(15,2),
    memory_pattern_id       uuid              REFERENCES memory_patterns(id) ON DELETE SET NULL,
    created_at              timestamptz       NOT NULL DEFAULT NOW(),
    updated_at              timestamptz       NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN risks.severity_score       IS 'Composite score: probability × impact (0–25 scale)';
COMMENT ON COLUMN risks.monte_carlo_p50_days IS 'Monte Carlo P50 schedule impact in days';
COMMENT ON COLUMN risks.monte_carlo_p80_days IS 'Monte Carlo P80 schedule impact in days (conservative)';
COMMENT ON COLUMN risks.memory_pattern_id    IS 'Links to Organizational Memory pattern for similar historical risks';

CREATE TRIGGER trg_risks_updated_at
    BEFORE UPDATE ON risks FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE risk_assessments (
    id               uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_id          uuid              NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    project_id       uuid              NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    assessed_by      uuid              NOT NULL REFERENCES users(id),
    probability      probability_level NOT NULL,
    impact           impact_level      NOT NULL,
    severity_score   numeric(4,2)      NOT NULL,
    assessment_notes text,
    assessed_at      timestamptz       NOT NULL DEFAULT NOW(),
    created_at       timestamptz       NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------

CREATE TABLE risk_mitigations (
    id                  uuid               PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_id             uuid               NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    project_id          uuid               NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid               NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title               text               NOT NULL,
    description         text,
    status              mitigation_status  NOT NULL DEFAULT 'planned',
    owner_id            uuid               REFERENCES users(id) ON DELETE SET NULL,
    due_date            date,
    completed_at        date,
    effectiveness_score numeric(3,2)       CHECK (effectiveness_score >= 0 AND effectiveness_score <= 1),
    created_at          timestamptz        NOT NULL DEFAULT NOW(),
    updated_at          timestamptz        NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN risk_mitigations.effectiveness_score IS 'Post-mitigation effectiveness 0.00–1.00 (feeds Memory Engine)';

CREATE TRIGGER trg_risk_mitigations_updated_at
    BEFORE UPDATE ON risk_mitigations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SECTION 25: DECISION TABLES
-- Note: decisions.chosen_option_id references decision_options (circular).
-- FK constraint added via ALTER TABLE after decision_options is created.
-- =============================================================================

CREATE TABLE decisions (
    id                   uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id           uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id            uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    decision_code        text,
    type                 decision_type   NOT NULL,
    status               decision_status NOT NULL DEFAULT 'draft',
    title                text            NOT NULL,
    description          text,
    context              text,
    owner_id             uuid            REFERENCES users(id) ON DELETE SET NULL,
    decision_deadline    date,
    chosen_option_id     uuid,           -- FK added after decision_options is created
    institutional_matches jsonb          NOT NULL DEFAULT '[]',
    created_at           timestamptz     NOT NULL DEFAULT NOW(),
    updated_at           timestamptz     NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN decisions.chosen_option_id      IS 'FK to decision_options.id; added via ALTER TABLE below';
COMMENT ON COLUMN decisions.institutional_matches IS 'Array of {pattern_id, summary, confidence} from Organizational Memory Engine';

CREATE TRIGGER trg_decisions_updated_at
    BEFORE UPDATE ON decisions FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE decision_options (
    id                            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id                   uuid        NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    project_id                    uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    option_label                  text        NOT NULL,
    description                   text,
    pros                          text,
    cons                          text,
    estimated_cost_impact         numeric(15,2),
    estimated_schedule_impact_days integer,
    evidence_refs                 jsonb       NOT NULL DEFAULT '[]',
    is_chosen                     boolean     NOT NULL DEFAULT false,
    created_at                    timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN decision_options.evidence_refs IS 'Array of {evidence_id, description} supporting this option';

-- Resolve circular FK: decisions.chosen_option_id → decision_options.id
ALTER TABLE decisions
    ADD CONSTRAINT fk_decisions_chosen_option
        FOREIGN KEY (chosen_option_id) REFERENCES decision_options(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------------

CREATE TABLE decision_approvals (
    id             uuid                    PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id    uuid                    NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    project_id     uuid                    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    approver_id    uuid                    NOT NULL REFERENCES users(id),
    sequence_order integer                 NOT NULL DEFAULT 1,
    status         approval_workflow_status NOT NULL DEFAULT 'not_started',
    approved_at    timestamptz,
    comments       text,
    created_at     timestamptz             NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 26: COORDINATION TABLES (new v5)
-- Coordination Engine closes the loop: Event → Action → Acknowledge → Execute → Verify → Close
-- =============================================================================

CREATE TABLE coordination_items (
    id                  uuid                 PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid                 NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid                 NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_event_type   text,
    source_event_id     uuid,
    source_entity_type  text,
    source_entity_id    uuid,
    action_description  text                 NOT NULL,
    assigned_to         uuid                 REFERENCES users(id) ON DELETE SET NULL,
    due_date            date,
    status              coordination_status  NOT NULL DEFAULT 'pending',
    priority            text                 NOT NULL DEFAULT 'medium',
    acknowledged_at     timestamptz,
    acknowledged_by     uuid                 REFERENCES users(id) ON DELETE SET NULL,
    executed_at         timestamptz,
    verified_at         timestamptz,
    overdue_at          timestamptz,
    created_at          timestamptz          NOT NULL DEFAULT NOW(),
    updated_at          timestamptz          NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN coordination_items.source_event_type  IS 'Originating event type (e.g., drawing_status_changed, vendor_delay_detected)';
COMMENT ON COLUMN coordination_items.source_entity_type IS 'Entity type that generated this item (activity, drawing, dispatch, etc.)';
COMMENT ON COLUMN coordination_items.priority           IS 'critical | high | medium | low';

CREATE TRIGGER trg_coordination_items_updated_at
    BEFORE UPDATE ON coordination_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE coordination_closures (
    id                   uuid                      PRIMARY KEY DEFAULT gen_random_uuid(),
    coordination_item_id uuid                      NOT NULL REFERENCES coordination_items(id) ON DELETE CASCADE,
    project_id           uuid                      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id            uuid                      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    closure_type         coordination_closure_type NOT NULL,
    verified_by          uuid                      REFERENCES users(id) ON DELETE SET NULL,
    evidence_ref         text,
    evidence_id          uuid                      REFERENCES evidences(id) ON DELETE SET NULL,
    closure_notes        text,
    closed_at            timestamptz               NOT NULL DEFAULT NOW(),
    created_at           timestamptz               NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 27: READINESS TABLES (new v5)
-- Six readiness gates with structured criteria per Readiness Engine
-- =============================================================================

CREATE TABLE readiness_gates (
    id                  uuid                  PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          uuid                  NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid                  NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    gate_type           readiness_gate_type   NOT NULL,
    status              readiness_gate_status NOT NULL DEFAULT 'not_started',
    completion_pct      numeric(5,2)          NOT NULL DEFAULT 0
                            CHECK (completion_pct >= 0 AND completion_pct <= 100),
    blocking_items      jsonb                 NOT NULL DEFAULT '[]',
    responsible_user_id uuid                  REFERENCES users(id) ON DELETE SET NULL,
    target_ready_date   date,
    evaluated_at        timestamptz,
    created_at          timestamptz           NOT NULL DEFAULT NOW(),
    updated_at          timestamptz           NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, gate_type)
);

COMMENT ON COLUMN readiness_gates.blocking_items IS 'Array of {criterion_id, description, entity_ref} blocking items';

CREATE TRIGGER trg_readiness_gates_updated_at
    BEFORE UPDATE ON readiness_gates FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE readiness_criteria (
    id              uuid                      PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id         uuid                      NOT NULL REFERENCES readiness_gates(id) ON DELETE CASCADE,
    project_id      uuid                      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id       uuid                      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    criterion_text  text                      NOT NULL,
    status          readiness_criteria_status NOT NULL DEFAULT 'not_checked',
    entity_type     text,
    entity_id       uuid,
    checked_by      uuid                      REFERENCES users(id) ON DELETE SET NULL,
    checked_at      timestamptz,
    waiver_reason   text,
    notes           text,
    created_at      timestamptz               NOT NULL DEFAULT NOW(),
    updated_at      timestamptz               NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN readiness_criteria.entity_type   IS 'Optional link to specific entity this criterion evaluates';
COMMENT ON COLUMN readiness_criteria.waiver_reason IS 'Required when status = waived; justification text';

CREATE TRIGGER trg_readiness_criteria_updated_at
    BEFORE UPDATE ON readiness_criteria FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE readiness_scores (
    id                   uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id           uuid                NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id            uuid                NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type          text                NOT NULL,
    entity_id            uuid                NOT NULL,
    gate_type            readiness_gate_type NOT NULL,
    score                numeric(4,3)        NOT NULL DEFAULT 0,
    blocking_items_count integer             NOT NULL DEFAULT 0,
    blocking_items       jsonb               NOT NULL DEFAULT '[]',
    computed_at          timestamptz         NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, entity_type, entity_id, gate_type)
);

-- =============================================================================
-- SECTION 28: SIMULATION TABLES (new v5)
-- What-if scenario modeling over the PIG
-- =============================================================================

CREATE TABLE simulation_scenarios (
    id               uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       uuid              NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id        uuid              NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name             text              NOT NULL,
    description      text,
    status           simulation_status NOT NULL DEFAULT 'draft',
    base_snapshot_id uuid,
    created_by       uuid              REFERENCES users(id) ON DELETE SET NULL,
    completed_at     timestamptz,
    created_at       timestamptz       NOT NULL DEFAULT NOW(),
    updated_at       timestamptz       NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN simulation_scenarios.base_snapshot_id IS 'UUID of the project state snapshot this scenario is based on';

CREATE TRIGGER trg_simulation_scenarios_updated_at
    BEFORE UPDATE ON simulation_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE simulation_inputs (
    id               uuid               PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id      uuid               NOT NULL REFERENCES simulation_scenarios(id) ON DELETE CASCADE,
    project_id       uuid               NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_type      text,
    entity_id        uuid,
    perturbation_type perturbation_type NOT NULL,
    parameter        text               NOT NULL,
    original_value   jsonb,
    simulated_value  jsonb,
    rationale        text,
    created_at       timestamptz        NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN simulation_inputs.parameter       IS 'Field being perturbed (e.g., planned_finish, quantity, cost)';
COMMENT ON COLUMN simulation_inputs.original_value  IS 'Baseline value before perturbation';
COMMENT ON COLUMN simulation_inputs.simulated_value IS 'Perturbed value for scenario run';

-- ---------------------------------------------------------------------------

CREATE TABLE simulation_results (
    id                    uuid                   PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id           uuid                   NOT NULL REFERENCES simulation_scenarios(id) ON DELETE CASCADE,
    project_id            uuid                   NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    output_type           simulation_output_type NOT NULL,
    delta_schedule_days   integer                NOT NULL DEFAULT 0,
    delta_cost            numeric(15,2)          NOT NULL DEFAULT 0,
    impact_summary        jsonb                  NOT NULL DEFAULT '{}',
    critical_path_changes jsonb                  NOT NULL DEFAULT '[]',
    recommendations       jsonb                  NOT NULL DEFAULT '[]',
    confidence_score      numeric(3,2)           CHECK (confidence_score >= 0 AND confidence_score <= 1),
    computed_at           timestamptz            NOT NULL DEFAULT NOW(),
    created_at            timestamptz            NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN simulation_results.delta_schedule_days   IS 'Net schedule impact in days (positive = delay)';
COMMENT ON COLUMN simulation_results.critical_path_changes IS 'Array of {activity_id, old_float, new_float, became_critical}';
COMMENT ON COLUMN simulation_results.recommendations       IS 'Engine-generated mitigation recommendations for this scenario';

-- =============================================================================
-- SECTION 29: PROJECT INTELLIGENCE GRAPH TABLES (new v5)
-- PIG is the architectural brain: live property graph, updated event-driven via Pub/Sub
-- All engines query the PIG — engines do NOT maintain their own relationship models
-- =============================================================================

CREATE TABLE graph_nodes (
    id             uuid                  PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     uuid                  NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id      uuid                  NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type    graph_node_entity_type NOT NULL,
    entity_id      uuid                  NOT NULL,
    attributes     jsonb                 NOT NULL DEFAULT '{}',
    last_synced_at timestamptz,
    created_at     timestamptz           NOT NULL DEFAULT NOW(),
    updated_at     timestamptz           NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, entity_type, entity_id)
);

COMMENT ON COLUMN graph_nodes.entity_id  IS 'UUID of the actual entity in its domain table';
COMMENT ON COLUMN graph_nodes.attributes IS 'Denormalized entity attributes for graph traversal performance';

CREATE TRIGGER trg_graph_nodes_updated_at
    BEFORE UPDATE ON graph_nodes FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

-- Edge type registry: authoritative list of valid edge semantics
CREATE TABLE graph_edge_types (
    edge_type        text        PRIMARY KEY,
    description      text        NOT NULL,
    is_directed      boolean     NOT NULL DEFAULT true,
    weight_semantics text,
    created_at       timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  graph_edge_types              IS 'Registry of valid PIG edge types; joined by graph_edges for validation';
COMMENT ON COLUMN graph_edge_types.weight_semantics IS 'Describes what weight means for this edge type (e.g., dependency_strength, impact_magnitude)';

-- Seed edge type registry
INSERT INTO graph_edge_types (edge_type, description, is_directed, weight_semantics) VALUES
    ('blocks',         'Source blocks target from starting/completing',      true,  'blocking_severity'),
    ('supplies_to',    'Vendor/package supplies material to activity',        true,  'delivery_confidence'),
    ('approved_by',    'Entity approved by approver',                        true,  'approval_weight'),
    ('impacts',        'Change/event impacts target entity',                 true,  'impact_magnitude'),
    ('depends_on',     'Activity depends on target activity',                true,  'dependency_strength'),
    ('supersedes',     'Drawing revision supersedes earlier revision',        true,  'recency'),
    ('conflicts_with', 'Entity conflicts with target (consistency alert)',    false, 'conflict_severity'),
    ('delivers_for',   'Dispatch delivers material for activity',             true,  'delivery_completeness'),
    ('reviews',        'User reviews document/drawing/evidence',              true,  'review_weight'),
    ('assigned_to',    'Task assigned to person',                            true,  'assignment_weight'),
    ('coordinates_with','Coordination link between entities',                false, 'coordination_priority'),
    ('escalates_to',   'Issue escalated to higher authority',                true,  'urgency'),
    ('preceded_by',    'Activity preceded by target in sequence',            true,  'sequence_order'),
    ('parallel_with',  'Activity runs parallel with target',                 false, 'resource_overlap'),
    ('requires',       'Entity requires target before proceeding',           true,  'criticality'),
    ('satisfies',      'Evidence/criteria satisfies requirement',             true,  'satisfaction_score'),
    ('verifies',       'Inspection/review verifies entity',                  true,  'verification_confidence'),
    ('closes',         'Resolution closes open item',                        true,  'closure_weight'),
    ('monitors',       'Risk/system monitors target entity',                 true,  'monitoring_frequency'),
    ('triggers',       'Event triggers target action/item',                  true,  'trigger_strength'),
    ('owns',           'Person/org owns entity',                             true,  'ownership_weight'),
    ('raised_by',      'Issue/risk raised by person',                        true,  'attribution_weight'),
    ('resolved_by',    'Issue resolved by person/action',                    true,  'resolution_weight'),
    ('references',     'Entity references another entity',                   true,  'reference_weight'),
    ('superseded_by',  'Entity superseded by newer entity',                  true,  'recency'),
    ('mitigates',      'Mitigation action mitigates risk',                   true,  'mitigation_effectiveness'),
    ('raises_risk_to', 'Event raises risk exposure for target',              true,  'risk_delta'),
    ('clears',         'Action clears blocking condition',                   true,  'clearing_strength'),
    ('gates',          'Readiness gate controls target entity',              true,  'gate_strength'),
    ('reports_to',     'Person reports to another in org hierarchy',         true,  'hierarchy_level');

-- ---------------------------------------------------------------------------

CREATE TABLE graph_edges (
    id             uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     uuid           NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id      uuid           NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_node_id uuid           NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id uuid           NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type      graph_edge_type NOT NULL,
    weight         numeric(5,4)   NOT NULL DEFAULT 1.0
                       CHECK (weight >= 0 AND weight <= 1),
    metadata       jsonb          NOT NULL DEFAULT '{}',
    created_at     timestamptz    NOT NULL DEFAULT NOW(),
    expires_at     timestamptz
);

COMMENT ON COLUMN graph_edges.weight     IS 'Edge weight 0.0000–1.0000; semantics vary by edge_type (see graph_edge_types)';
COMMENT ON COLUMN graph_edges.expires_at IS 'Optional edge expiry for time-bound relationships; NULL = permanent';

-- =============================================================================
-- SECTION 30: ORGANIZATIONAL MEMORY — RECORDS AND CONTRIBUTIONS
-- memory_patterns already defined in Section 23 (before risks needed it)
-- =============================================================================

CREATE TABLE memory_records (
    id               uuid               PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       uuid               NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id        uuid               NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    record_type      memory_record_type NOT NULL,
    category         memory_category    NOT NULL DEFAULT 'neutral',
    entity_type      text,
    entity_ids       jsonb              NOT NULL DEFAULT '[]',
    summary          text               NOT NULL,
    detail           jsonb              NOT NULL DEFAULT '{}',
    frequency        integer            NOT NULL DEFAULT 1,
    first_occurred_at timestamptz       NOT NULL DEFAULT NOW(),
    last_occurred_at timestamptz        NOT NULL DEFAULT NOW(),
    confidence_score numeric(3,2)       NOT NULL DEFAULT 0.5
                         CHECK (confidence_score >= 0 AND confidence_score <= 1),
    created_at       timestamptz        NOT NULL DEFAULT NOW(),
    updated_at       timestamptz        NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN memory_records.entity_ids       IS 'Array of UUIDs of entities involved in this memory record';
COMMENT ON COLUMN memory_records.frequency        IS 'Number of times this pattern has occurred in this project';
COMMENT ON COLUMN memory_records.confidence_score IS 'Confidence 0.00–1.00 that this record is relevant and accurate';

CREATE TRIGGER trg_memory_records_updated_at
    BEFORE UPDATE ON memory_records FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE memory_contributions (
    id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_pattern_id   uuid        NOT NULL REFERENCES memory_patterns(id) ON DELETE CASCADE,
    project_id          uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id           uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    record_id           uuid        NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
    contributed_at      timestamptz NOT NULL DEFAULT NOW(),
    contribution_weight numeric(3,2) NOT NULL DEFAULT 1.0
                            CHECK (contribution_weight >= 0 AND contribution_weight <= 1),
    created_at          timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN memory_contributions.contribution_weight IS 'Weight of this record in updating the pattern confidence score';

-- =============================================================================
-- SECTION 31: REPORTING, FORECASTING, AND SUPPORTING TABLES
-- =============================================================================

CREATE TABLE reports (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id    uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type         report_type NOT NULL,
    period_start date,
    period_end   date,
    status       text        NOT NULL DEFAULT 'draft',
    generated_by uuid        REFERENCES users(id) ON DELETE SET NULL,
    generated_at timestamptz,
    file_ref     text,
    gcp_object   text,
    metadata     jsonb,
    created_at   timestamptz NOT NULL DEFAULT NOW(),
    updated_at   timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN reports.status IS 'draft | generating | ready | distributed';

CREATE TRIGGER trg_reports_updated_at
    BEFORE UPDATE ON reports FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE report_sections (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id      uuid        NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    section_type   text        NOT NULL,
    title          text        NOT NULL,
    content_json   jsonb,
    narrative_text text,
    order_index    integer     NOT NULL DEFAULT 0,
    generated_at   timestamptz,
    created_at     timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN report_sections.narrative_text IS 'AI-generated narrative section; produced by AI Orchestration Engine via Claude API';

-- ---------------------------------------------------------------------------

CREATE TABLE recommendations (
    id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id             uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title                 text        NOT NULL,
    description           text,
    priority              text        NOT NULL DEFAULT 'medium',
    entity_type           text,
    entity_id             uuid,
    engines_contributing  jsonb,
    evidence_refs         jsonb,
    projected_outcome     text,
    recommendation_score  numeric(4,2),
    status                text        NOT NULL DEFAULT 'active',
    dismissed_at          timestamptz,
    dismissed_by          uuid        REFERENCES users(id) ON DELETE SET NULL,
    created_at            timestamptz NOT NULL DEFAULT NOW(),
    updated_at            timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN recommendations.priority             IS 'critical | high | medium | low';
COMMENT ON COLUMN recommendations.engines_contributing IS 'Array of engine identifiers that contributed to this recommendation';
COMMENT ON COLUMN recommendations.evidence_refs        IS 'Array of {evidence_id, description} supporting this recommendation';
COMMENT ON COLUMN recommendations.recommendation_score IS 'Confidence-weighted importance score 0–10';
COMMENT ON COLUMN recommendations.status               IS 'active | acknowledged | implemented | dismissed | superseded';

CREATE TRIGGER trg_recommendations_updated_at
    BEFORE UPDATE ON recommendations FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE forecasts (
    id                       uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id               uuid            NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id                uuid            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    domain                   forecast_domain NOT NULL,
    current_value            numeric(15,2),
    forecast_value           numeric(15,2),
    forecast_date            date,
    confidence_interval_low  numeric(15,2),
    confidence_interval_high numeric(15,2),
    trend_direction          text,
    engines_contributing     jsonb,
    computed_at              timestamptz     NOT NULL DEFAULT NOW(),
    created_at               timestamptz     NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN forecasts.trend_direction      IS 'improving | stable | deteriorating | at_risk';
COMMENT ON COLUMN forecasts.engines_contributing IS 'Array of engine names that provided inputs to this forecast';

-- ---------------------------------------------------------------------------

CREATE TABLE alignment_gaps (
    id               uuid                 PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       uuid                 NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id        uuid                 NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    status           alignment_gap_status NOT NULL DEFAULT 'open',
    gap_type         text                 NOT NULL,
    stakeholder_ids  jsonb                NOT NULL DEFAULT '[]',
    information_type text,
    description      text,
    severity         text,
    created_at       timestamptz          NOT NULL DEFAULT NOW(),
    resolved_at      timestamptz,
    updated_at       timestamptz          NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN alignment_gaps.gap_type        IS 'missing_acknowledgment | information_lag | conflicting_instructions | unread_critical_update';
COMMENT ON COLUMN alignment_gaps.stakeholder_ids IS 'Array of user UUIDs involved in this alignment gap';

CREATE TRIGGER trg_alignment_gaps_updated_at
    BEFORE UPDATE ON alignment_gaps FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE consistency_contradictions (
    id                         uuid                    PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id                 uuid                    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id                  uuid                    NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    severity                   contradiction_severity  NOT NULL,
    entity_pair                jsonb                   NOT NULL,
    conflict_type              text                    NOT NULL,
    description                text,
    resolution_recommendation  text,
    status                     text                    NOT NULL DEFAULT 'open',
    resolved_by                uuid                    REFERENCES users(id) ON DELETE SET NULL,
    resolved_at                timestamptz,
    created_at                 timestamptz             NOT NULL DEFAULT NOW(),
    updated_at                 timestamptz             NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN consistency_contradictions.entity_pair  IS '{entity_type_a, entity_id_a, entity_type_b, entity_id_b} pair in conflict';
COMMENT ON COLUMN consistency_contradictions.conflict_type IS 'version_mismatch | date_conflict | quantity_discrepancy | status_conflict';
COMMENT ON COLUMN consistency_contradictions.status        IS 'open | acknowledged | resolved | waived';

CREATE TRIGGER trg_consistency_contradictions_updated_at
    BEFORE UPDATE ON consistency_contradictions FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ---------------------------------------------------------------------------

CREATE TABLE notifications (
    id           uuid                NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id   uuid                NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id    uuid                NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id      uuid                NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type         notification_type   NOT NULL,
    status       notification_status NOT NULL DEFAULT 'pending',
    subject      text                NOT NULL,
    body         text,
    metadata     jsonb,
    sent_at      timestamptz,
    delivered_at timestamptz,
    created_at   timestamptz         NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------

-- Transactional outbox for reliable event publishing to Pub/Sub (27 topics)
CREATE TABLE outbox_events (
    id          uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  uuid          NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id   uuid          NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    topic       text          NOT NULL,
    event_type  text          NOT NULL,
    payload     jsonb         NOT NULL,
    status      outbox_status NOT NULL DEFAULT 'pending',
    published_at timestamptz,
    retry_count integer       NOT NULL DEFAULT 0,
    error       text,
    created_at  timestamptz   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  outbox_events       IS 'Transactional outbox pattern: events written here, published to Pub/Sub by outbox worker';
COMMENT ON COLUMN outbox_events.topic IS 'Pub/Sub topic name (one of 27 Green PM topics)';

-- ---------------------------------------------------------------------------

-- Idempotency key store for at-most-once API operations
CREATE TABLE idempotency_keys (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash     text        NOT NULL,
    processed_at timestamptz NOT NULL,
    expires_at   timestamptz NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE (key_hash)
);

COMMENT ON TABLE  idempotency_keys          IS 'Prevents duplicate processing of API requests with same idempotency key';
COMMENT ON COLUMN idempotency_keys.key_hash IS 'SHA-256 hash of the idempotency key header value';

-- ---------------------------------------------------------------------------

CREATE TABLE file_attachments (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   uuid        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id    uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type  text,
    entity_id    uuid,
    filename     text        NOT NULL,
    content_type text,
    size_bytes   bigint,
    gcp_bucket   text        NOT NULL,
    gcp_object   text        NOT NULL,
    uploaded_by  uuid        REFERENCES users(id) ON DELETE SET NULL,
    created_at   timestamptz NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------

CREATE TABLE audit_logs (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id  uuid        REFERENCES projects(id) ON DELETE SET NULL,
    user_id     uuid        REFERENCES users(id) ON DELETE SET NULL,
    action      text        NOT NULL,
    entity_type text,
    entity_id   uuid,
    old_value   jsonb,
    new_value   jsonb,
    ip_address  inet,
    created_at  timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  audit_logs        IS 'Immutable audit trail; no updated_at — rows are never modified';
COMMENT ON COLUMN audit_logs.action IS 'CREATE | UPDATE | DELETE | LOGIN | EXPORT | APPROVE | REJECT';

-- =============================================================================
-- SECTION 32: INDEXES (135+ total)
-- Groups: Core platform, Schedule, Evidence, Drawing/Doc, Change, Equipment,
--         Supply Chain, Risk, Decision, Coordination, Readiness, Simulation,
--         PIG, Memory, Supporting
-- =============================================================================

-- ---------------------------------------------------------------------------
-- CORE PLATFORM
-- ---------------------------------------------------------------------------
CREATE INDEX idx_tenants_plan                ON tenants (plan);
CREATE INDEX idx_projects_tenant_id          ON projects (tenant_id);
CREATE INDEX idx_projects_tenant_status      ON projects (tenant_id, status);
CREATE INDEX idx_projects_tenant_phase       ON projects (tenant_id, phase);
CREATE INDEX idx_users_tenant_id             ON users (tenant_id);
CREATE INDEX idx_users_tenant_active         ON users (tenant_id, is_active) WHERE is_active = true;
CREATE INDEX idx_users_email                 ON users (email);
CREATE INDEX idx_user_project_access_user_id    ON user_project_access (user_id);
CREATE INDEX idx_user_project_access_project_id ON user_project_access (project_id);
CREATE INDEX idx_user_project_access_role    ON user_project_access (project_id, role);

-- ---------------------------------------------------------------------------
-- SCHEDULE
-- ---------------------------------------------------------------------------
CREATE INDEX idx_wbs_elements_project_id     ON wbs_elements (project_id);
CREATE INDEX idx_wbs_elements_tenant_id      ON wbs_elements (tenant_id);
CREATE INDEX idx_wbs_elements_parent_id      ON wbs_elements (parent_id);
CREATE INDEX idx_wbs_elements_project_level  ON wbs_elements (project_id, level);

CREATE INDEX idx_activities_project_id       ON activities (project_id);
CREATE INDEX idx_activities_tenant_id        ON activities (tenant_id);
CREATE INDEX idx_activities_wbs_id           ON activities (wbs_id);
CREATE INDEX idx_activities_responsible      ON activities (responsible_user_id);
CREATE INDEX idx_activities_project_status   ON activities (project_id, status);
CREATE INDEX idx_activities_project_type     ON activities (project_id, type);
CREATE INDEX idx_activities_critical         ON activities (project_id, is_critical) WHERE is_critical = true;
CREATE INDEX idx_activities_planned_finish   ON activities (project_id, planned_finish);
CREATE INDEX idx_activities_tenant_created   ON activities (tenant_id, created_at DESC);

CREATE INDEX idx_milestones_project_id       ON milestones (project_id);
CREATE INDEX idx_milestones_tenant_id        ON milestones (tenant_id);
CREATE INDEX idx_milestones_activity_id      ON milestones (activity_id);
CREATE INDEX idx_milestones_responsible      ON milestones (responsible_user_id);
CREATE INDEX idx_milestones_project_status   ON milestones (project_id, status);
CREATE INDEX idx_milestones_planned_date     ON milestones (project_id, planned_date);

CREATE INDEX idx_activity_deps_project_id    ON activity_dependencies (project_id);
CREATE INDEX idx_activity_deps_predecessor   ON activity_dependencies (predecessor_id);
CREATE INDEX idx_activity_deps_successor     ON activity_dependencies (successor_id);

-- ---------------------------------------------------------------------------
-- EVIDENCE
-- ---------------------------------------------------------------------------
CREATE INDEX idx_evidences_project_id        ON evidences (project_id);
CREATE INDEX idx_evidences_tenant_id         ON evidences (tenant_id);
CREATE INDEX idx_evidences_entity            ON evidences (project_id, entity_type, entity_id);
CREATE INDEX idx_evidences_captured_by       ON evidences (captured_by);
CREATE INDEX idx_evidences_project_status    ON evidences (project_id, status);
CREATE INDEX idx_evidences_capture_type      ON evidences (project_id, capture_type);
CREATE INDEX idx_evidences_reliability       ON evidences (project_id, reliability_tier);
CREATE INDEX idx_evidences_captured_at       ON evidences (project_id, captured_at DESC);

CREATE INDEX idx_evidence_reviews_evidence   ON evidence_reviews (evidence_id);
CREATE INDEX idx_evidence_reviews_reviewer   ON evidence_reviews (reviewer_id);

-- Unique index enforced by UNIQUE constraint, but explicit for plan visibility:
-- evidence_scores: UNIQUE(project_id, entity_type, entity_id) already indexed

-- ---------------------------------------------------------------------------
-- DRAWING / DOCUMENT
-- ---------------------------------------------------------------------------
CREATE INDEX idx_drawings_project_id         ON drawings (project_id);
CREATE INDEX idx_drawings_tenant_id          ON drawings (tenant_id);
CREATE INDEX idx_drawings_responsible        ON drawings (responsible_user_id);
CREATE INDEX idx_drawings_project_type       ON drawings (project_id, type);
CREATE INDEX idx_drawings_project_status     ON drawings (project_id, current_status);
CREATE INDEX idx_drawings_discipline         ON drawings (project_id, discipline);

CREATE INDEX idx_drawing_revisions_drawing   ON drawing_revisions (drawing_id);
CREATE INDEX idx_drawing_revisions_project   ON drawing_revisions (project_id);
CREATE INDEX idx_drawing_revisions_tenant    ON drawing_revisions (tenant_id);
CREATE INDEX idx_drawing_revisions_current   ON drawing_revisions (drawing_id, is_current) WHERE is_current = true;
CREATE INDEX idx_drawing_revisions_issued_by ON drawing_revisions (issued_by);

CREATE INDEX idx_rfis_drawing_id             ON rfis (drawing_id);
CREATE INDEX idx_rfis_project_id             ON rfis (project_id);
CREATE INDEX idx_rfis_tenant_id              ON rfis (tenant_id);
CREATE INDEX idx_rfis_raised_by              ON rfis (raised_by);
CREATE INDEX idx_rfis_project_status         ON rfis (project_id, status);

CREATE INDEX idx_documents_project_id        ON documents (project_id);
CREATE INDEX idx_documents_tenant_id         ON documents (tenant_id);
CREATE INDEX idx_documents_project_type      ON documents (project_id, type);
CREATE INDEX idx_documents_uploaded_by       ON documents (uploaded_by);

-- ---------------------------------------------------------------------------
-- CHANGE
-- ---------------------------------------------------------------------------
CREATE INDEX idx_changes_project_id          ON changes (project_id);
CREATE INDEX idx_changes_tenant_id           ON changes (tenant_id);
CREATE INDEX idx_changes_requestor           ON changes (requestor_id);
CREATE INDEX idx_changes_project_status      ON changes (project_id, status);
CREATE INDEX idx_changes_project_type        ON changes (project_id, type);
CREATE INDEX idx_changes_tenant_created      ON changes (tenant_id, created_at DESC);

CREATE INDEX idx_change_impacts_change_id    ON change_impacts (change_id);
CREATE INDEX idx_change_impacts_project_id   ON change_impacts (project_id);
CREATE INDEX idx_change_impacts_assessed_by  ON change_impacts (assessed_by);

CREATE INDEX idx_change_approvals_change_id  ON change_approvals (change_id);
CREATE INDEX idx_change_approvals_approver   ON change_approvals (approver_id);
CREATE INDEX idx_change_approvals_project_status ON change_approvals (project_id, status);

-- ---------------------------------------------------------------------------
-- SUPPLY CHAIN & EQUIPMENT
-- ---------------------------------------------------------------------------
CREATE INDEX idx_vendors_tenant_id           ON vendors (tenant_id);
CREATE INDEX idx_vendors_tenant_status       ON vendors (tenant_id, status);
CREATE INDEX idx_vendors_approved_by         ON vendors (approved_by);

CREATE INDEX idx_vendor_scores_vendor_id     ON vendor_scores (vendor_id);
CREATE INDEX idx_vendor_scores_project_id    ON vendor_scores (project_id);
CREATE INDEX idx_vendor_scores_tenant_id     ON vendor_scores (tenant_id);
CREATE INDEX idx_vendor_scores_computed_at   ON vendor_scores (vendor_id, computed_at DESC);

CREATE INDEX idx_pos_project_id              ON purchase_orders (project_id);
CREATE INDEX idx_pos_tenant_id               ON purchase_orders (tenant_id);
CREATE INDEX idx_pos_vendor_id               ON purchase_orders (vendor_id);
CREATE INDEX idx_pos_project_status          ON purchase_orders (project_id, status);
CREATE INDEX idx_pos_delivery_due            ON purchase_orders (project_id, delivery_due_date);

CREATE INDEX idx_dispatches_po_id            ON dispatches (po_id);
CREATE INDEX idx_dispatches_project_id       ON dispatches (project_id);
CREATE INDEX idx_dispatches_tenant_id        ON dispatches (tenant_id);
CREATE INDEX idx_dispatches_vendor_id        ON dispatches (vendor_id);
CREATE INDEX idx_dispatches_project_status   ON dispatches (project_id, status);
CREATE INDEX idx_dispatches_current_stage    ON dispatches (project_id, current_stage);
CREATE INDEX idx_dispatches_delivery_date    ON dispatches (project_id, planned_delivery_date);

CREATE INDEX idx_dispatch_stages_dispatch_id ON dispatch_stages (dispatch_id);
CREATE INDEX idx_dispatch_stages_project_id  ON dispatch_stages (project_id);
CREATE INDEX idx_dispatch_stages_evidence_id ON dispatch_stages (evidence_id);

CREATE INDEX idx_material_packages_project_id ON material_packages (project_id);
CREATE INDEX idx_material_packages_tenant_id  ON material_packages (tenant_id);
CREATE INDEX idx_material_packages_po_id      ON material_packages (po_id);
CREATE INDEX idx_material_packages_vendor_id  ON material_packages (vendor_id);
CREATE INDEX idx_material_packages_type       ON material_packages (project_id, type);

CREATE INDEX idx_material_items_package_id    ON material_items (package_id);
CREATE INDEX idx_material_items_project_id    ON material_items (project_id);
CREATE INDEX idx_material_items_dispatch_id   ON material_items (dispatch_id);

CREATE INDEX idx_shipments_dispatch_id        ON shipments (dispatch_id);
CREATE INDEX idx_shipments_project_id         ON shipments (project_id);
CREATE INDEX idx_shipments_project_status     ON shipments (project_id, status);
CREATE INDEX idx_shipments_eta                ON shipments (project_id, eta);

CREATE INDEX idx_equipment_project_id         ON equipment_items (project_id);
CREATE INDEX idx_equipment_tenant_id          ON equipment_items (tenant_id);
CREATE INDEX idx_equipment_vendor_id          ON equipment_items (vendor_id);
CREATE INDEX idx_equipment_po_id              ON equipment_items (po_id);
CREATE INDEX idx_equipment_activity_id        ON equipment_items (activity_id);
CREATE INDEX idx_equipment_project_status     ON equipment_items (project_id, status);

CREATE INDEX idx_equipment_insp_equipment_id  ON equipment_inspections (equipment_id);
CREATE INDEX idx_equipment_insp_project_id    ON equipment_inspections (project_id);
CREATE INDEX idx_equipment_insp_project_status ON equipment_inspections (project_id, status);
CREATE INDEX idx_equipment_insp_inspector     ON equipment_inspections (inspector_id);

-- ---------------------------------------------------------------------------
-- RISK
-- ---------------------------------------------------------------------------
CREATE INDEX idx_risks_project_id             ON risks (project_id);
CREATE INDEX idx_risks_tenant_id              ON risks (tenant_id);
CREATE INDEX idx_risks_owner_id               ON risks (owner_id);
CREATE INDEX idx_risks_project_status         ON risks (project_id, status);
CREATE INDEX idx_risks_project_category       ON risks (project_id, category);
CREATE INDEX idx_risks_project_probability    ON risks (project_id, probability);
CREATE INDEX idx_risks_memory_pattern         ON risks (memory_pattern_id);
CREATE INDEX idx_risks_tenant_created         ON risks (tenant_id, created_at DESC);

CREATE INDEX idx_risk_assessments_risk_id     ON risk_assessments (risk_id);
CREATE INDEX idx_risk_assessments_project_id  ON risk_assessments (project_id);
CREATE INDEX idx_risk_assessments_assessed_by ON risk_assessments (assessed_by);

CREATE INDEX idx_risk_mitigations_risk_id     ON risk_mitigations (risk_id);
CREATE INDEX idx_risk_mitigations_project_id  ON risk_mitigations (project_id);
CREATE INDEX idx_risk_mitigations_owner_id    ON risk_mitigations (owner_id);
CREATE INDEX idx_risk_mitigations_status      ON risk_mitigations (project_id, status);

-- ---------------------------------------------------------------------------
-- DECISION
-- ---------------------------------------------------------------------------
CREATE INDEX idx_decisions_project_id         ON decisions (project_id);
CREATE INDEX idx_decisions_tenant_id          ON decisions (tenant_id);
CREATE INDEX idx_decisions_owner_id           ON decisions (owner_id);
CREATE INDEX idx_decisions_project_status     ON decisions (project_id, status);
CREATE INDEX idx_decisions_project_type       ON decisions (project_id, type);
CREATE INDEX idx_decisions_deadline           ON decisions (project_id, decision_deadline);
CREATE INDEX idx_decisions_tenant_created     ON decisions (tenant_id, created_at DESC);

CREATE INDEX idx_decision_options_decision_id ON decision_options (decision_id);
CREATE INDEX idx_decision_options_project_id  ON decision_options (project_id);
CREATE INDEX idx_decision_options_is_chosen   ON decision_options (decision_id, is_chosen) WHERE is_chosen = true;

CREATE INDEX idx_decision_approvals_decision  ON decision_approvals (decision_id);
CREATE INDEX idx_decision_approvals_approver  ON decision_approvals (approver_id);
CREATE INDEX idx_decision_approvals_status    ON decision_approvals (project_id, status);

-- ---------------------------------------------------------------------------
-- COORDINATION (new v5)
-- ---------------------------------------------------------------------------
CREATE INDEX idx_coord_items_project_id       ON coordination_items (project_id);
CREATE INDEX idx_coord_items_tenant_id        ON coordination_items (tenant_id);
CREATE INDEX idx_coord_items_assigned_to      ON coordination_items (assigned_to);
CREATE INDEX idx_coord_items_project_status   ON coordination_items (project_id, status);
CREATE INDEX idx_coord_items_due_date         ON coordination_items (project_id, due_date);
-- Partial index for polling pending/overdue items
CREATE INDEX idx_coord_items_pending          ON coordination_items (project_id, due_date)
    WHERE status IN ('pending', 'acknowledged', 'executing', 'overdue');
CREATE INDEX idx_coord_items_source_entity    ON coordination_items (project_id, source_entity_type, source_entity_id);
CREATE INDEX idx_coord_items_ack_by           ON coordination_items (acknowledged_by);

CREATE INDEX idx_coord_closures_item_id       ON coordination_closures (coordination_item_id);
CREATE INDEX idx_coord_closures_project_id    ON coordination_closures (project_id);
CREATE INDEX idx_coord_closures_verified_by   ON coordination_closures (verified_by);
CREATE INDEX idx_coord_closures_evidence_id   ON coordination_closures (evidence_id);

-- ---------------------------------------------------------------------------
-- READINESS (new v5)
-- ---------------------------------------------------------------------------
CREATE INDEX idx_readiness_gates_project_id   ON readiness_gates (project_id);
CREATE INDEX idx_readiness_gates_tenant_id    ON readiness_gates (tenant_id);
CREATE INDEX idx_readiness_gates_responsible  ON readiness_gates (responsible_user_id);
CREATE INDEX idx_readiness_gates_status       ON readiness_gates (project_id, status);

CREATE INDEX idx_readiness_criteria_gate_id   ON readiness_criteria (gate_id);
CREATE INDEX idx_readiness_criteria_project_id ON readiness_criteria (project_id);
CREATE INDEX idx_readiness_criteria_status    ON readiness_criteria (gate_id, status);
CREATE INDEX idx_readiness_criteria_entity    ON readiness_criteria (project_id, entity_type, entity_id);
CREATE INDEX idx_readiness_criteria_checked_by ON readiness_criteria (checked_by);

-- readiness_scores: UNIQUE(project_id, entity_type, entity_id, gate_type) already indexed

-- ---------------------------------------------------------------------------
-- SIMULATION (new v5)
-- ---------------------------------------------------------------------------
CREATE INDEX idx_sim_scenarios_project_id     ON simulation_scenarios (project_id);
CREATE INDEX idx_sim_scenarios_tenant_id      ON simulation_scenarios (tenant_id);
CREATE INDEX idx_sim_scenarios_status         ON simulation_scenarios (project_id, status);
CREATE INDEX idx_sim_scenarios_created_by     ON simulation_scenarios (created_by);

CREATE INDEX idx_sim_inputs_scenario_id       ON simulation_inputs (scenario_id);
CREATE INDEX idx_sim_inputs_project_id        ON simulation_inputs (project_id);
CREATE INDEX idx_sim_inputs_entity            ON simulation_inputs (scenario_id, entity_type, entity_id);

CREATE INDEX idx_sim_results_scenario_id      ON simulation_results (scenario_id);
CREATE INDEX idx_sim_results_project_id       ON simulation_results (project_id);
CREATE INDEX idx_sim_results_output_type      ON simulation_results (scenario_id, output_type);

-- ---------------------------------------------------------------------------
-- PROJECT INTELLIGENCE GRAPH (new v5)
-- ---------------------------------------------------------------------------
-- Primary graph traversal index: lookup node for any entity
CREATE INDEX idx_graph_nodes_project_id       ON graph_nodes (project_id);
CREATE INDEX idx_graph_nodes_tenant_id        ON graph_nodes (tenant_id);
-- entity_type + entity_id lookup (covered by UNIQUE but explicit for planner)
CREATE INDEX idx_graph_nodes_entity_type      ON graph_nodes (project_id, entity_type);
CREATE INDEX idx_graph_nodes_last_synced      ON graph_nodes (project_id, last_synced_at DESC);

-- Edge traversal indexes
CREATE INDEX idx_graph_edges_project_id       ON graph_edges (project_id);
CREATE INDEX idx_graph_edges_source_node      ON graph_edges (project_id, source_node_id, edge_type);
CREATE INDEX idx_graph_edges_target_node      ON graph_edges (project_id, target_node_id, edge_type);
CREATE INDEX idx_graph_edges_edge_type        ON graph_edges (project_id, edge_type);
-- Active edges (non-expired)
CREATE INDEX idx_graph_edges_active           ON graph_edges (project_id, edge_type, weight)
    WHERE expires_at IS NULL OR expires_at > NOW();
-- Bi-directional traversal
CREATE INDEX idx_graph_edges_source_target    ON graph_edges (source_node_id, target_node_id, edge_type);

-- ---------------------------------------------------------------------------
-- ORGANIZATIONAL MEMORY (new v5)
-- ---------------------------------------------------------------------------
CREATE INDEX idx_memory_patterns_tenant_id    ON memory_patterns (tenant_id);
CREATE INDEX idx_memory_patterns_type         ON memory_patterns (tenant_id, pattern_type);
CREATE INDEX idx_memory_patterns_confidence   ON memory_patterns (tenant_id, confidence_score DESC);
CREATE INDEX idx_memory_patterns_last_matched ON memory_patterns (tenant_id, last_matched_at DESC);

CREATE INDEX idx_memory_records_project_id    ON memory_records (project_id);
CREATE INDEX idx_memory_records_tenant_id     ON memory_records (tenant_id);
CREATE INDEX idx_memory_records_type          ON memory_records (project_id, record_type);
CREATE INDEX idx_memory_records_category      ON memory_records (project_id, category);
CREATE INDEX idx_memory_records_entity        ON memory_records (project_id, entity_type);
CREATE INDEX idx_memory_records_last_occurred ON memory_records (tenant_id, last_occurred_at DESC);

CREATE INDEX idx_memory_contributions_pattern ON memory_contributions (memory_pattern_id);
CREATE INDEX idx_memory_contributions_project ON memory_contributions (project_id);
CREATE INDEX idx_memory_contributions_record  ON memory_contributions (record_id);

-- ---------------------------------------------------------------------------
-- SUPPORTING TABLES
-- ---------------------------------------------------------------------------
CREATE INDEX idx_reports_project_id           ON reports (project_id);
CREATE INDEX idx_reports_tenant_id            ON reports (tenant_id);
CREATE INDEX idx_reports_project_type         ON reports (project_id, type);
CREATE INDEX idx_reports_generated_by         ON reports (generated_by);
CREATE INDEX idx_reports_tenant_created       ON reports (tenant_id, created_at DESC);

CREATE INDEX idx_report_sections_report_id    ON report_sections (report_id);
CREATE INDEX idx_report_sections_order        ON report_sections (report_id, order_index);

CREATE INDEX idx_recommendations_project_id   ON recommendations (project_id);
CREATE INDEX idx_recommendations_tenant_id    ON recommendations (tenant_id);
CREATE INDEX idx_recommendations_project_status ON recommendations (project_id, status);
CREATE INDEX idx_recommendations_entity       ON recommendations (project_id, entity_type, entity_id);
CREATE INDEX idx_recommendations_score        ON recommendations (project_id, recommendation_score DESC)
    WHERE status = 'active';
CREATE INDEX idx_recommendations_dismissed_by ON recommendations (dismissed_by);

CREATE INDEX idx_forecasts_project_id         ON forecasts (project_id);
CREATE INDEX idx_forecasts_tenant_id          ON forecasts (tenant_id);
CREATE INDEX idx_forecasts_project_domain     ON forecasts (project_id, domain);
CREATE INDEX idx_forecasts_computed_at        ON forecasts (project_id, domain, computed_at DESC);

CREATE INDEX idx_alignment_gaps_project_id    ON alignment_gaps (project_id);
CREATE INDEX idx_alignment_gaps_tenant_id     ON alignment_gaps (tenant_id);
CREATE INDEX idx_alignment_gaps_project_status ON alignment_gaps (project_id, status);
CREATE INDEX idx_alignment_gaps_open          ON alignment_gaps (project_id, created_at DESC)
    WHERE status = 'open';

CREATE INDEX idx_contradictions_project_id    ON consistency_contradictions (project_id);
CREATE INDEX idx_contradictions_tenant_id     ON consistency_contradictions (tenant_id);
CREATE INDEX idx_contradictions_severity      ON consistency_contradictions (project_id, severity);
CREATE INDEX idx_contradictions_project_status ON consistency_contradictions (project_id, status);
CREATE INDEX idx_contradictions_resolved_by   ON consistency_contradictions (resolved_by);

CREATE INDEX idx_notifications_project_id     ON notifications (project_id);
CREATE INDEX idx_notifications_tenant_id      ON notifications (tenant_id);
CREATE INDEX idx_notifications_user_id        ON notifications (user_id);
CREATE INDEX idx_notifications_user_status    ON notifications (user_id, status);
CREATE INDEX idx_notifications_project_type   ON notifications (project_id, type);
CREATE INDEX idx_notifications_pending        ON notifications (project_id, created_at)
    WHERE status = 'pending';

CREATE INDEX idx_outbox_project_id            ON outbox_events (project_id);
CREATE INDEX idx_outbox_tenant_id             ON outbox_events (tenant_id);
CREATE INDEX idx_outbox_topic                 ON outbox_events (topic, status);
-- Critical polling index: outbox worker queries by status + created_at
CREATE INDEX idx_outbox_pending               ON outbox_events (status, created_at)
    WHERE status = 'pending';
CREATE INDEX idx_outbox_failed_retry          ON outbox_events (status, retry_count)
    WHERE status = 'failed';

-- Cleanup index for expired idempotency keys
CREATE INDEX idx_idempotency_expires_at       ON idempotency_keys (expires_at);

CREATE INDEX idx_file_attachments_project_id  ON file_attachments (project_id);
CREATE INDEX idx_file_attachments_tenant_id   ON file_attachments (tenant_id);
CREATE INDEX idx_file_attachments_entity      ON file_attachments (project_id, entity_type, entity_id);
CREATE INDEX idx_file_attachments_uploaded_by ON file_attachments (uploaded_by);

CREATE INDEX idx_audit_logs_tenant_id         ON audit_logs (tenant_id);
CREATE INDEX idx_audit_logs_project_id        ON audit_logs (project_id);
CREATE INDEX idx_audit_logs_user_id           ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_entity            ON audit_logs (entity_type, entity_id);
CREATE INDEX idx_audit_logs_tenant_created    ON audit_logs (tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_project_created   ON audit_logs (project_id, created_at DESC);

-- =============================================================================
-- SECTION 33: ROW LEVEL SECURITY (RLS)
-- Policy: tenant isolation via app.current_tenant_id session variable
-- Set before queries: SET LOCAL app.current_tenant_id = '<uuid>';
-- All tables enabled; super_admin bypass via separate DB role if needed.
-- =============================================================================

-- Core Platform
ALTER TABLE tenants                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE users                       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_project_access         ENABLE ROW LEVEL SECURITY;

-- Vendors
ALTER TABLE vendors                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_scores               ENABLE ROW LEVEL SECURITY;

-- Schedule
ALTER TABLE wbs_elements                ENABLE ROW LEVEL SECURITY;
ALTER TABLE activities                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE milestones                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_dependencies       ENABLE ROW LEVEL SECURITY;

-- Evidence
ALTER TABLE evidences                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_reviews            ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_scores             ENABLE ROW LEVEL SECURITY;

-- Drawing / Document
ALTER TABLE drawings                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE drawing_revisions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE rfis                        ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents                   ENABLE ROW LEVEL SECURITY;

-- Change
ALTER TABLE changes                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_impacts              ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_approvals            ENABLE ROW LEVEL SECURITY;

-- Supply Chain
ALTER TABLE purchase_orders             ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatches                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch_stages             ENABLE ROW LEVEL SECURITY;
ALTER TABLE material_packages           ENABLE ROW LEVEL SECURITY;
ALTER TABLE material_items              ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments                   ENABLE ROW LEVEL SECURITY;

-- Equipment
ALTER TABLE equipment_items             ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_inspections       ENABLE ROW LEVEL SECURITY;

-- Risk
ALTER TABLE risks                       ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_mitigations            ENABLE ROW LEVEL SECURITY;

-- Decision
ALTER TABLE decisions                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_options            ENABLE ROW LEVEL SECURITY;
ALTER TABLE decision_approvals          ENABLE ROW LEVEL SECURITY;

-- Coordination (v5)
ALTER TABLE coordination_items          ENABLE ROW LEVEL SECURITY;
ALTER TABLE coordination_closures       ENABLE ROW LEVEL SECURITY;

-- Readiness (v5)
ALTER TABLE readiness_gates             ENABLE ROW LEVEL SECURITY;
ALTER TABLE readiness_criteria          ENABLE ROW LEVEL SECURITY;
ALTER TABLE readiness_scores            ENABLE ROW LEVEL SECURITY;

-- Simulation (v5)
ALTER TABLE simulation_scenarios        ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_inputs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_results          ENABLE ROW LEVEL SECURITY;

-- PIG (v5)
ALTER TABLE graph_nodes                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges                 ENABLE ROW LEVEL SECURITY;

-- Memory (v5)
ALTER TABLE memory_patterns             ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_records              ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_contributions        ENABLE ROW LEVEL SECURITY;

-- Supporting
ALTER TABLE reports                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_sections             ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations             ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE alignment_gaps              ENABLE ROW LEVEL SECURITY;
ALTER TABLE consistency_contradictions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications               ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox_events               ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_attachments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs                  ENABLE ROW LEVEL SECURITY;

-- graph_edge_types and idempotency_keys have no tenant_id; no RLS needed
-- (graph_edge_types is static config; idempotency_keys enforced by key_hash)

-- =============================================================================
-- RLS POLICIES — tenant isolation
-- Pattern: USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
-- =============================================================================

-- Core Platform
CREATE POLICY tenant_isolation ON tenants
    USING (id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON user_project_access
    USING (user_id IN (
        SELECT id FROM users
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

-- Vendors
CREATE POLICY tenant_isolation ON vendors
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON vendor_scores
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Schedule
CREATE POLICY tenant_isolation ON wbs_elements
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON activities
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON milestones
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON activity_dependencies
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

-- Evidence
CREATE POLICY tenant_isolation ON evidences
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON evidence_reviews
    USING (evidence_id IN (
        SELECT id FROM evidences
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON evidence_scores
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Drawing / Document
CREATE POLICY tenant_isolation ON drawings
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON drawing_revisions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON rfis
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Change
CREATE POLICY tenant_isolation ON changes
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON change_impacts
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON change_approvals
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

-- Supply Chain
CREATE POLICY tenant_isolation ON purchase_orders
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON dispatches
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON dispatch_stages
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON material_packages
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON material_items
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON shipments
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Equipment
CREATE POLICY tenant_isolation ON equipment_items
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON equipment_inspections
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Risk
CREATE POLICY tenant_isolation ON risks
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON risk_assessments
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON risk_mitigations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Decision
CREATE POLICY tenant_isolation ON decisions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON decision_options
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON decision_approvals
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

-- Coordination (v5)
CREATE POLICY tenant_isolation ON coordination_items
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON coordination_closures
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Readiness (v5)
CREATE POLICY tenant_isolation ON readiness_gates
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON readiness_criteria
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON readiness_scores
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Simulation (v5)
CREATE POLICY tenant_isolation ON simulation_scenarios
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON simulation_inputs
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON simulation_results
    USING (project_id IN (
        SELECT id FROM projects
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

-- PIG (v5)
CREATE POLICY tenant_isolation ON graph_nodes
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON graph_edges
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Memory (v5)
CREATE POLICY tenant_isolation ON memory_patterns
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON memory_records
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON memory_contributions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Supporting
CREATE POLICY tenant_isolation ON reports
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON report_sections
    USING (report_id IN (
        SELECT id FROM reports
        WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
    ));

CREATE POLICY tenant_isolation ON recommendations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON forecasts
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON alignment_gaps
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON consistency_contradictions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON notifications
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON outbox_events
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON file_attachments
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation ON audit_logs
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- =============================================================================
-- SECTION 34: COMMIT AND VERIFICATION
-- =============================================================================

COMMIT;

-- ---------------------------------------------------------------------------
-- Post-deployment verification queries
-- Run these after applying the schema to confirm object counts
-- ---------------------------------------------------------------------------

-- Table count (expect 56+)
SELECT COUNT(*) AS table_count
FROM pg_tables
WHERE schemaname = 'public';

-- All table names
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- ENUM count (expect 65+)
SELECT COUNT(*) AS enum_count
FROM pg_type
WHERE typtype = 'e'
  AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public');

-- Index count (expect 135+)
SELECT COUNT(*) AS index_count
FROM pg_indexes
WHERE schemaname = 'public';

-- RLS-enabled tables
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND rowsecurity = true
ORDER BY tablename;

-- Trigger count
SELECT COUNT(*) AS trigger_count
FROM information_schema.triggers
WHERE trigger_schema = 'public';

-- =============================================================================
-- END OF GREEN PM v5 DATABASE SCHEMA
-- =============================================================================
