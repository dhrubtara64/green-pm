"""Phase 0 Foundation — 10 tables, RLS, indexes, graph_edge_types seed data

Revision ID: 001
Revises:
Create Date: 2026-08-03

Tables: tenants, users, projects, user_project_access, graph_edge_types,
        graph_nodes, graph_edges, outbox_events, idempotency_keys, audit_logs

RLS: enabled on all tenant-scoped tables via app.current_tenant_id session var
     audit_logs is additionally append-only (no UPDATE, no DELETE)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ENTITY_TYPES = [
    "activity", "milestone", "drawing", "document", "equipment",
    "vendor", "dispatch", "evidence", "change", "decision",
    "risk", "issue", "gate", "wbs", "package", "shipment",
    "claim", "payment", "inspection", "commissioning_item",
    "organizational_unit", "person",
]

_EDGE_TYPES_SEED = [
    ("BLOCKS",           "Source activity/gate blocks target from starting",            True),
    ("SUPPLIES_TO",      "Vendor supplies material or equipment to activity",            True),
    ("APPROVED_BY",      "Entity requires approval from person or committee",            True),
    ("IMPACTS",          "Change or risk impacts target entity",                         True),
    ("DEPENDS_ON",       "Activity depends on completion of target (CPM finish-start)",  True),
    ("SUPERSEDES",       "New drawing or document supersedes older version",             True),
    ("CONFLICTS_WITH",   "Entity has a contradictory relationship with target",          False),
    ("DELIVERS_FOR",     "Dispatch or shipment delivers material for target activity",   True),
    ("REVIEWS",          "Person reviews document or drawing",                           True),
    ("ASSIGNED_TO",      "Activity or task is assigned to a person",                    True),
    ("COORDINATES_WITH", "Activity must coordinate timing with target",                  False),
    ("ESCALATES_TO",     "Issue or risk escalates to person or committee",              True),
    ("PRECEDED_BY",      "Activity is preceded by target in CPM network",               True),
    ("PARALLEL_WITH",    "Activity runs in parallel with target activity",               False),
    ("REQUIRES",         "Activity requires drawing, document, or equipment",           True),
    ("SATISFIES",        "Evidence or document satisfies a requirement or gate",         True),
    ("VERIFIES",         "Inspection or test verifies quality of target",               True),
    ("CLOSES",           "Decision or corrective action closes risk or issue",          True),
    ("MONITORS",         "Person or system monitors target entity",                     True),
    ("TRIGGERS",         "Event or condition triggers target action or alert",           True),
    ("OWNS",             "Person or org unit owns responsibility for target",           True),
    ("RAISED_BY",        "Risk or issue was raised by a person",                        True),
    ("RESOLVED_BY",      "Risk or issue was resolved by a person",                      True),
    ("REFERENCES",       "Document or drawing references target",                       True),
    ("SUPERSEDED_BY",    "Entity has been superseded by a newer version",               True),
    ("MITIGATES",        "Action or plan mitigates target risk",                        True),
    ("RAISES_RISK_TO",   "Activity or change increases risk exposure for target",       True),
    ("CLEARS",           "Gate or inspection clears target for next phase",             True),
    ("GATES",            "Gate or prerequisite blocks target activity from starting",   True),
    ("REPORTS_TO",       "Person reports to another person in org hierarchy",           True),
]

_RLS_TABLES = [
    "users",
    "projects",
    "user_project_access",
    "graph_nodes",
    "graph_edges",
    "outbox_events",
    "idempotency_keys",
    "audit_logs",
]

# Shorthand for the RLS expression used in every policy
_RLS_EXPR = "tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID"


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    entity_list = ", ".join(f"'{t}'" for t in _ENTITY_TYPES)
    op.execute(f"CREATE TYPE graph_node_entity_type AS ENUM ({entity_list})")

    # ── tenants ───────────────────────────────────────────────────────────────
    # No RLS on tenants — it IS the isolation root. Access controlled in app layer.
    op.execute("""
        CREATE TABLE tenants (
            id         UUID        NOT NULL DEFAULT gen_random_uuid(),
            name       VARCHAR(100) NOT NULL,
            plan       VARCHAR(20)  NOT NULL DEFAULT 'pilot',
            domain     VARCHAR(255),
            is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT tenants_pkey       PRIMARY KEY (id),
            CONSTRAINT tenants_plan_check CHECK (plan IN ('pilot','professional','enterprise'))
        )
    """)

    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE users (
            id         UUID         NOT NULL DEFAULT gen_random_uuid(),
            tenant_id  UUID         NOT NULL,
            email      VARCHAR(255) NOT NULL,
            name       VARCHAR(255) NOT NULL,
            role       VARCHAR(30)  NOT NULL DEFAULT 'engineer',
            is_active  BOOLEAN      NOT NULL DEFAULT FALSE,
            google_sub VARCHAR(255),
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT users_pkey              PRIMARY KEY (id),
            CONSTRAINT users_tenant_fk         FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            CONSTRAINT users_tenant_email_uq   UNIQUE (tenant_id, email),
            CONSTRAINT users_role_check        CHECK (role IN (
                'super_admin','tenant_admin','project_manager',
                'engineer','vendor_portal','executive','viewer'
            ))
        )
    """)

    # ── projects ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE projects (
            id           UUID         NOT NULL DEFAULT gen_random_uuid(),
            tenant_id    UUID         NOT NULL,
            name         VARCHAR(255) NOT NULL,
            project_code VARCHAR(50)  NOT NULL,
            status       VARCHAR(20)  NOT NULL DEFAULT 'active',
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT projects_pkey           PRIMARY KEY (id),
            CONSTRAINT projects_tenant_fk      FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            CONSTRAINT projects_code_uq        UNIQUE (tenant_id, project_code),
            CONSTRAINT projects_status_check   CHECK (status IN ('active','archived','on_hold'))
        )
    """)

    # ── user_project_access ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE user_project_access (
            id         UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id  UUID        NOT NULL,
            user_id    UUID        NOT NULL,
            project_id UUID        NOT NULL,
            role       VARCHAR(30) NOT NULL DEFAULT 'engineer',
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            granted_by UUID,
            CONSTRAINT upa_pkey           PRIMARY KEY (id),
            CONSTRAINT upa_tenant_fk      FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
            CONSTRAINT upa_user_fk        FOREIGN KEY (user_id)    REFERENCES users(id),
            CONSTRAINT upa_project_fk     FOREIGN KEY (project_id) REFERENCES projects(id),
            CONSTRAINT upa_granted_by_fk  FOREIGN KEY (granted_by) REFERENCES users(id),
            CONSTRAINT upa_user_proj_uq   UNIQUE (user_id, project_id)
        )
    """)

    # ── graph_edge_types (seed table, no RLS — global catalogue) ─────────────
    op.execute("""
        CREATE TABLE graph_edge_types (
            edge_type   VARCHAR(50) NOT NULL,
            description TEXT        NOT NULL,
            is_directed BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT graph_edge_types_pkey PRIMARY KEY (edge_type)
        )
    """)

    # ── graph_nodes ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE graph_nodes (
            id             UUID                   NOT NULL DEFAULT gen_random_uuid(),
            project_id     UUID                   NOT NULL,
            tenant_id      UUID                   NOT NULL,
            entity_type    graph_node_entity_type NOT NULL,
            entity_id      UUID                   NOT NULL,
            attributes     JSONB                  NOT NULL DEFAULT '{}',
            last_synced_at TIMESTAMPTZ            NOT NULL DEFAULT NOW(),
            created_at     TIMESTAMPTZ            NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ            NOT NULL DEFAULT NOW(),
            CONSTRAINT graph_nodes_pkey       PRIMARY KEY (id),
            CONSTRAINT graph_nodes_project_fk FOREIGN KEY (project_id) REFERENCES projects(id),
            CONSTRAINT graph_nodes_tenant_fk  FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
            CONSTRAINT graph_nodes_entity_uq  UNIQUE (project_id, entity_type, entity_id)
        )
    """)

    # ── graph_edges ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE graph_edges (
            id             UUID         NOT NULL DEFAULT gen_random_uuid(),
            project_id     UUID         NOT NULL,
            tenant_id      UUID         NOT NULL,
            source_node_id UUID         NOT NULL,
            target_node_id UUID         NOT NULL,
            edge_type      VARCHAR(50)  NOT NULL,
            weight         NUMERIC(5,4) NOT NULL DEFAULT 1.0,
            metadata       JSONB        NOT NULL DEFAULT '{}',
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            expires_at     TIMESTAMPTZ,
            CONSTRAINT graph_edges_pkey        PRIMARY KEY (id),
            CONSTRAINT graph_edges_project_fk  FOREIGN KEY (project_id)     REFERENCES projects(id),
            CONSTRAINT graph_edges_tenant_fk   FOREIGN KEY (tenant_id)      REFERENCES tenants(id),
            CONSTRAINT graph_edges_source_fk   FOREIGN KEY (source_node_id) REFERENCES graph_nodes(id),
            CONSTRAINT graph_edges_target_fk   FOREIGN KEY (target_node_id) REFERENCES graph_nodes(id),
            CONSTRAINT graph_edges_type_fk     FOREIGN KEY (edge_type)      REFERENCES graph_edge_types(edge_type),
            CONSTRAINT graph_edges_weight_chk  CHECK (weight >= 0.0 AND weight <= 1.0)
        )
    """)

    # ── outbox_events ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE outbox_events (
            id             UUID         NOT NULL DEFAULT gen_random_uuid(),
            tenant_id      UUID         NOT NULL,
            topic          VARCHAR(100) NOT NULL,
            event_type     VARCHAR(100) NOT NULL,
            schema_version VARCHAR(20)  NOT NULL DEFAULT '1.0.0',
            payload        JSONB        NOT NULL DEFAULT '{}',
            status         VARCHAR(20)  NOT NULL DEFAULT 'pending',
            correlation_id UUID,
            causation_id   UUID,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            published_at   TIMESTAMPTZ,
            retry_count    INTEGER      NOT NULL DEFAULT 0,
            last_error     TEXT,
            CONSTRAINT outbox_events_pkey       PRIMARY KEY (id),
            CONSTRAINT outbox_events_tenant_fk  FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            CONSTRAINT outbox_events_status_chk CHECK (status IN ('pending','published','failed','dead'))
        )
    """)

    # ── idempotency_keys ──────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE idempotency_keys (
            key          VARCHAR(255) NOT NULL,
            tenant_id    UUID         NOT NULL,
            processed_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            expires_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW() + INTERVAL '7 days',
            CONSTRAINT idempotency_keys_pkey      PRIMARY KEY (key),
            CONSTRAINT idempotency_keys_tenant_fk FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    """)

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE audit_logs (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID        NOT NULL,
            project_id  UUID,
            user_id     UUID,
            action      VARCHAR(20) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id   UUID,
            old_value   JSONB,
            new_value   JSONB,
            ip_address  VARCHAR(45),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT audit_logs_pkey       PRIMARY KEY (id),
            CONSTRAINT audit_logs_tenant_fk  FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
            CONSTRAINT audit_logs_project_fk FOREIGN KEY (project_id) REFERENCES projects(id),
            CONSTRAINT audit_logs_user_fk    FOREIGN KEY (user_id)    REFERENCES users(id),
            CONSTRAINT audit_logs_action_chk CHECK (action IN ('CREATE','UPDATE','DELETE','VIEW'))
        )
    """)

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.execute("CREATE INDEX ix_users_tenant          ON users (tenant_id)")
    op.execute("CREATE INDEX ix_projects_tenant       ON projects (tenant_id)")
    op.execute("CREATE INDEX ix_upa_tenant            ON user_project_access (tenant_id)")
    op.execute("CREATE INDEX ix_upa_user              ON user_project_access (user_id)")
    op.execute("CREATE INDEX ix_upa_project           ON user_project_access (project_id)")
    op.execute("CREATE INDEX ix_graph_nodes_tenant    ON graph_nodes (tenant_id)")
    op.execute("CREATE INDEX ix_graph_nodes_proj_type ON graph_nodes (project_id, entity_type)")
    op.execute("CREATE INDEX ix_graph_edges_tenant    ON graph_edges (tenant_id)")
    op.execute("CREATE INDEX ix_graph_edges_source    ON graph_edges (project_id, source_node_id, edge_type)")
    op.execute("CREATE INDEX ix_graph_edges_target    ON graph_edges (project_id, target_node_id, edge_type)")
    op.execute("CREATE INDEX ix_graph_edges_active    ON graph_edges (project_id, edge_type) WHERE expires_at IS NULL")
    op.execute("CREATE INDEX ix_outbox_tenant_status  ON outbox_events (tenant_id, status, created_at)")
    op.execute("CREATE INDEX ix_outbox_pending        ON outbox_events (created_at) WHERE status = 'pending'")
    op.execute("CREATE INDEX ix_idem_tenant           ON idempotency_keys (tenant_id)")
    op.execute("CREATE INDEX ix_idem_expires          ON idempotency_keys (expires_at)")
    op.execute("CREATE INDEX ix_audit_tenant_time     ON audit_logs (tenant_id, created_at)")
    op.execute("CREATE INDEX ix_audit_entity          ON audit_logs (entity_type, entity_id)")

    # ── Row Level Security ────────────────────────────────────────────────────
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({_RLS_EXPR})
            WITH CHECK ({_RLS_EXPR})
        """)

    # audit_logs is append-only — no UPDATE or DELETE ever permitted
    op.execute("CREATE POLICY audit_logs_no_update ON audit_logs FOR UPDATE USING (FALSE)")
    op.execute("CREATE POLICY audit_logs_no_delete ON audit_logs FOR DELETE USING (FALSE)")

    # ── Seed data: graph_edge_types ───────────────────────────────────────────
    edge_type_table = sa.table(
        "graph_edge_types",
        sa.column("edge_type",   sa.String),
        sa.column("description", sa.Text),
        sa.column("is_directed", sa.Boolean),
    )
    op.bulk_insert(edge_type_table, [
        {"edge_type": et, "description": desc, "is_directed": directed}
        for et, desc, directed in _EDGE_TYPES_SEED
    ])


def downgrade() -> None:
    # Drop in reverse dependency order
    for table in reversed(_RLS_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("DROP TABLE IF EXISTS graph_edge_types CASCADE")
    op.execute("DROP TABLE IF EXISTS user_project_access CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")
    op.execute("DROP TYPE IF EXISTS graph_node_entity_type")
