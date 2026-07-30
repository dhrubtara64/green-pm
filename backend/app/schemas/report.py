from datetime import datetime
from pydantic import BaseModel


class ReportOut(BaseModel):
    id: str
    draft_content: str
    edited_content: str | None
    created_at: datetime
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}


class ReportEditRequest(BaseModel):
    edited_content: str


class ReportSendRequest(BaseModel):
    pass
