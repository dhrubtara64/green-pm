from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    activity_id: str
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    evidence_refs: list[str] = []  # EvidenceItem IDs cited in the answer
