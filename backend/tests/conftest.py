"""Tests sur une vraie base PostgreSQL (boh_test), migrée avec Alembic à chaque run."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://boh:boh@localhost:5434/boh_test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")
os.environ["AI_PROVIDER"] = "mock"
os.environ.setdefault("STORAGE_DIR", str(__import__("tempfile").mkdtemp(prefix="boh-test-")))

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Organization, Role, Team, User  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "Test-password-123"
_HASH = hash_password(PASSWORD)


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE ai_suggestions, attachments, comments, request_events, requests, sla_policies, "
                "categories, accounts, audit_log, user_teams, users, teams, organizations "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def make_org(db: Session, name: str = "Org test") -> dict[str, User | Team | Organization]:
    """Une organisation avec une équipe et un utilisateur par rôle."""
    org = Organization(name=name, is_synthetic=True)
    db.add(org)
    db.flush()
    team = Team(organization_id=org.id, code="SUPPORT", name="Support")
    db.add(team)
    out: dict[str, User | Team | Organization] = {"org": org, "team": team}
    for role in Role:
        user = User(
            organization_id=org.id,
            email=f"{role.value.lower()}@{name.replace(' ', '').lower()}.example.com",
            full_name=f"{role.value.title()} Test",
            role=role,
            password_hash=_HASH,
            teams=[team] if role == Role.AGENT else [],
        )
        db.add(user)
        out[role.value] = user
    db.commit()
    return out


def login(client: TestClient, user: User) -> TestClient:
    r = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return client
