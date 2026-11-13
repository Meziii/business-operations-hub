from fastapi import FastAPI
from sqlalchemy import text

from app.ai import get_triage_provider
from app.deps import DbSession
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.requests.router import router as requests_router
from app.schemas import HealthOut

app = FastAPI(
    title="Business Operations Hub API",
    version="0.2.0",
    description="Opérations B2B : demandes, documents, connaissance, pilotage. Données synthétiques.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(requests_router)


@app.get("/api/health", response_model=HealthOut, tags=["system"])
def health(db: DbSession) -> HealthOut:
    db.execute(text("SELECT 1"))
    return HealthOut(status="ok", database="ok", ai_provider=get_triage_provider().name)
