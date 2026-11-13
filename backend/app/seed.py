"""Charge l'organisation de démonstration (données synthétiques). Idempotent.

    python -m app.seed

DEMO_PROFILE choisit l'habillage sectoriel (voir app/demo_profiles.py).
Le mot de passe des comptes de démonstration vient de DEMO_PASSWORD (voir .env.example).
"""

import sys

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.demo_profiles import PROFILES
from app.models import Organization, Team, User
from app.security import hash_password
from app.seed_requests import seed_requests


def main() -> int:
    settings = get_settings()
    if len(settings.demo_password) < 12:
        print("DEMO_PASSWORD absent ou trop court (12 caractères minimum) : seed ignoré.")
        return 1
    profile = PROFILES.get(settings.demo_profile)
    if profile is None:
        print(f"DEMO_PROFILE inconnu : {settings.demo_profile}. Choix : {', '.join(PROFILES)}.")
        return 1
    with SessionLocal() as db:
        existing = db.scalar(select(Organization).where(Organization.is_synthetic.is_(True)))
        if existing:
            n = seed_requests(db, existing)
            db.commit()
            print(f"Organisation de démonstration déjà présente. Demandes ajoutées : {n}.")
            return 0
        org = Organization(name=profile.organization, is_synthetic=True)
        db.add(org)
        db.flush()
        teams = {code: Team(organization_id=org.id, code=code, name=name) for code, name in profile.teams}
        db.add_all(teams.values())
        pw_hash = hash_password(settings.demo_password)
        for email, name, role, codes in profile.users:
            db.add(
                User(
                    organization_id=org.id,
                    email=email,
                    full_name=name,
                    role=role,
                    password_hash=pw_hash,
                    is_synthetic=True,
                    teams=[teams[c] for c in codes],
                )
            )
        db.flush()
        n = seed_requests(db, org)
        db.commit()
        print(
            f"{profile.organization} : {len(profile.teams)} équipes, {len(profile.users)} utilisateurs, "
            f"{n} demandes."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
