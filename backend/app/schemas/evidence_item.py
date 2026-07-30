from datetime import datetime
from pydantic import BaseModel


class EvidenceItemOut(BaseModel):
    id: str
    source_system: str
    ingesting_connector: str
    provenance_ref: str | None
    extracted_content: str
    source_excerpt: str | None
    relation_type: str
    source_reliability_signal: str
    timestamp: datetime
    ingested_at: datetime

    model_config = {"from_attributes": True}
