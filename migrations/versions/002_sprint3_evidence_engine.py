"""Sprint 3 — Evidence Engine tables: evidences, evidence_reviews, evidence_scores

Revision ID: 002
Revises: 001
Create Date: 2026-08-03

Adds:
  ENUMs: capture_type (12), evidence_status (6), evidence_review_outcome (3),
         reliability_tier (3)
  Tables: evidences, evidence_reviews, evidence_scores
  RLS: all three tables tenant-scoped via app.current_tenant_id
  Indexes: 8 covering entity lookups, status filtering, score retrieval
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RLS_EXPR = "tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID"

_RLS_TABLES = ["evidences", "evidence_reviews", "evidence_scores"]


def upgrade() -> None:
    # ── ENUMs ──────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE capture_type AS ENUM (
            'site_photo', 'site_video', 'voice_memo', 'document_upload',
            'qr_scan', 'form_submission', 'iot_sensor', 'drone_image',
            'surveyor_report', 'inspection_report', 'weather_log', 'financial_document'
        )
    """)
    op.execute("""
        CREATE TYPE evidence_status AS ENUM (
            'draft', 'submitted', 'under_review', 'approved', 'rejected', 'archived'
        )
    """)
    op.execute("""
        CREATE TYPE evidence_review_outcome AS ENUM (
            'approved', 'rejected', 'needs_revision'
        )
    """)
    op.execute("""
        CREATE TYPE reliability_tier AS ENUM (
            'primary', 'secondary', 'tertiary'
        )
    """)

    # ── evidences ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE evidences (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id       UUID         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            tenant_id        UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            entity_type      TEXT         NOT NULL,
            entity_id        UUID         NOT NULL,
            capture_type     capture_type     NOT NULL,
            status           evidence_status  NOT NULL DEFAULT 'draft',
            captured_by      UUID         REFERENCES users(id) ON DELETE SET NULL,
            captured_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            file_ref         TEXT,
            description      TEXT,
            location_lat     NUMERIC(9,6),
            location_lng     NUMERIC(9,6),
            gcp_bucket       TEXT,
            gcp_object       TEXT,
            reliability_tier reliability_tier NOT NULL DEFAULT 'secondary',
            metadata         JSONB        NOT NULL DEFAULT '{}',
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """)

    # ── evidence_reviews ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE evidence_reviews (
            id                 UUID                    PRIMARY KEY DEFAULT gen_random_uuid(),
            evidence_id        UUID                    NOT NULL REFERENCES evidences(id) ON DELETE CASCADE,
            tenant_id          UUID                    NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            reviewer_id        UUID                    NOT NULL REFERENCES users(id),
            outcome            evidence_review_outcome NOT NULL,
            comments           TEXT,
            reviewed_at        TIMESTAMPTZ             NOT NULL DEFAULT NOW(),
            reliability_weight NUMERIC(3,2)            NOT NULL DEFAULT 1.0
                                    CHECK (reliability_weight >= 0 AND reliability_weight <= 1),
            created_at         TIMESTAMPTZ             NOT NULL DEFAULT NOW()
        )
    """)

    # ── evidence_scores ────────────────────────────────────────────────────────
    # One row per (project, entity_type, entity_id) — recomputed on each ingestion
    op.execute("""
        CREATE TABLE evidence_scores (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id             UUID         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            tenant_id              UUID         NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            entity_type            TEXT         NOT NULL,
            entity_id              UUID         NOT NULL,
            score_value            NUMERIC(4,3) NOT NULL DEFAULT 0,
            source_count           INTEGER      NOT NULL DEFAULT 0,
            recency_decay          NUMERIC(4,3) NOT NULL DEFAULT 0,
            corroboration_ratio    NUMERIC(4,3) NOT NULL DEFAULT 0,
            capture_diversity      NUMERIC(4,3) NOT NULL DEFAULT 0,
            reliability_weight_avg NUMERIC(4,3) NOT NULL DEFAULT 0,
            computed_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (project_id, entity_type, entity_id)
        )
    """)

    # ── Indexes ────────────────────────────────────────────────────────────────
    op.execute("CREATE INDEX idx_evidences_entity ON evidences (project_id, entity_type, entity_id)")
    op.execute("CREATE INDEX idx_evidences_tenant_status ON evidences (tenant_id, status)")
    op.execute("CREATE INDEX idx_evidences_captured_at ON evidences (captured_at DESC)")
    op.execute("CREATE INDEX idx_evidences_capture_type ON evidences (capture_type, tenant_id)")
    op.execute("CREATE INDEX idx_evidence_reviews_evidence ON evidence_reviews (evidence_id)")
    op.execute("CREATE INDEX idx_evidence_scores_entity ON evidence_scores (project_id, entity_type, entity_id)")
    op.execute("CREATE INDEX idx_evidence_scores_tenant ON evidence_scores (tenant_id)")
    op.execute("CREATE INDEX idx_evidence_scores_value ON evidence_scores (score_value DESC)")

    # ── RLS ────────────────────────────────────────────────────────────────────
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({_RLS_EXPR})
            WITH CHECK ({_RLS_EXPR})
        """)

    # evidence_reviews: also accessible via the parent evidence's tenant
    op.execute("""
        CREATE POLICY evidence_reviews_tenant_check ON evidence_reviews
        AS PERMISSIVE FOR ALL TO PUBLIC
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID)
    """)


def downgrade() -> None:
    for table in reversed(_RLS_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for enum in ("reliability_tier", "evidence_review_outcome", "evidence_status", "capture_type"):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
