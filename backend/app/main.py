import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.ai import get_triage_provider
from app.deps import DbSession
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.documents.router import router as documents_router
from app.modules.documents.router import warm_quality_reports
from app.modules.requests.router import router as requests_router
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # L'évaluation hors-ligne de l'extraction est longue (OCR) : on la calcule en tâche de fond
    # dès le démarrage pour que la page « Qualité de l'extraction » réponde immédiatement.
    threading.Thread(target=warm_quality_reports, name="warm-quality", daemon=True).start()
    yield


app = FastAPI(
    title="Business Operations Hub API",
    version="0.2.0",
    description="Opérations B2B : demandes, documents, connaissance, pilotage. Données synthétiques.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(requests_router)
app.include_router(documents_router)


@app.get("/api/health", response_model=HealthOut, tags=["system"])
def health(db: DbSession) -> HealthOut:
    db.execute(text("SELECT 1"))
    return HealthOut(status="ok", database="ok", ai_provider=get_triage_provider().name)
