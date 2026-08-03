# Green PM v5 — Documentation Index

All architecture, product, technical, and implementation documents for Green PM v5 (Engineering Project Intelligence Platform).

## v5 Documents

### Architecture
| Document | Description |
|---|---|
| [Engineering Architecture](v5/architecture/GreenPM_v5_Engineering_Architecture.docx) | 24 Cloud Run services, 8 ADRs, infrastructure decisions |
| [Domain Model](v5/architecture/GreenPM_v5_Domain_Model.docx) | 22 bounded contexts, service ownership |
| [Project Intelligence Graph](v5/architecture/GreenPM_v5_Project_Intelligence_Graph.docx) | 22 node types, 30 edge types, PIG query patterns |
| [Event Model](v5/architecture/GreenPM_v5_Event_Model.docx) | 31 domain events, 27 Pub/Sub topics, outbox pattern |
| [Engineering Change Intelligence](v5/architecture/GreenPM_v5_Engineering_Change_Intelligence.docx) | Change lifecycle, impact propagation |

### Technical
| Document | Description |
|---|---|
| [Database Schema](v5/technical/GreenPM_v5_Database_Schema.sql) | 59 tables, 55 ENUMs, 248 indexes, 57 RLS policies |
| [API Contracts](v5/technical/GreenPM_v5_API_Contracts.yaml) | 151 paths, 148 schemas, all 17 engines |
| [Test Strategy](v5/technical/GreenPM_v5_Test_Strategy.docx) | 11 Evidence Score invariants, CI/CD gates |
| [Acceptance Criteria](v5/technical/GreenPM_v5_Acceptance_Criteria.docx) | 55 Gherkin scenarios (P0/P1/P2) |
| [Traceability Matrix](v5/technical/GreenPM_v5_Traceability_Matrix.docx) | 55 features, 9-dimension trace |

### Implementation
| Document | Description |
|---|---|
| [Engineering Standards](v5/implementation/GreenPM_v5_Engineering_Standards.docx) | Architectural rules — read before writing any code |
| [Phase 0 Implementation Epic](v5/implementation/GreenPM_v5_Phase0_Implementation_Epic.docx) | 19 stories, 91 pts, 3 sprints, acceptance criteria |
| [Sprint Backlog](v5/implementation/GreenPM_v5_Sprint_Backlog.docx) | All 19 sprints, 106 stories across 6 phases |

### Product
| Document | Description |
|---|---|
| [Executive Review Summary](v5/product/GreenPM_v5_Executive_Review_Summary.docx) | v5 vision, scoring, strategic rationale |
| [Product Principles](v5/product/GreenPM_v5_Product_Principles.docx) | 25 product principles |
| [Personas](v5/product/GreenPM_v5_Personas.docx) | 24 personas |
| [User Journeys](v5/product/GreenPM_v5_User_Journeys.docx) | 14 engine-centric journeys |
| [Engine Workflows](v5/product/GreenPM_v5_Engine_Workflows.docx) | 17 engines × 4 tables each |
| [Project Command Centre](v5/product/GreenPM_v5_Project_Command_Centre.docx) | 8 panels, real-time Firestore |
| [Green PM Studio](v5/product/GreenPM_v5_Green_PM_Studio.docx) | 15 builders |
| [Decision Centre](v5/product/GreenPM_v5_Decision_Centre.docx) | 10-state lifecycle |

### Wireframes
| Document | Description |
|---|---|
| [Wireframes](v5/wireframes/GreenPM_v5_Wireframes.html) | 34 screens, 14 navigation groups, interactive |

## Decisions (ADRs)

Architecture Decision Records live in [decisions/](decisions/). See [ADR_TEMPLATE.md](decisions/ADR_TEMPLATE.md).

Key decisions already encoded in the Engineering Architecture document:
- ADR-001: PostgreSQL graph tables over dedicated graph DB
- ADR-002: Transactional Outbox pattern for event publishing
- ADR-003: PgBouncer session mode for RLS
- ADR-004: Firestore replaces always-on WebSocket Cloud Run
- ADR-005: UUID v7 for entity PKs
- ADR-006: Engines query PIG, never maintain own relationship tables
- ADR-007: Activity Workspace co-ships with PIG in Phase 0
- ADR-008: AI Invisibility — no engine names or "AI" in UI

## Archive

- [v4 Engineering Architecture](archive/v4/GreenPM_v4_Engineering_Architecture.docx)
- [v4 Executive Review Summary](archive/v4/GreenPM_v4_Executive_Review_Summary.docx)
