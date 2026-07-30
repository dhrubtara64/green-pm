from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.api.routes import activities, ingestion, reports, chat

app = FastAPI(
    title="Green PM API",
    description="Engineering Project Intelligence Platform — Evidence-backed progress scoring for EPC projects.",
    version="1.0.0-demo",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activities.router)
app.include_router(ingestion.router)
app.include_router(reports.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup():
    create_tables()


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0-demo"}
