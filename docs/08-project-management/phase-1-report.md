# Bilan de la phase 1 — Fondations techniques

Date : 12/11/2026.

## Réalisé

| Livrable | Contenu |
|---|---|
| Backend | FastAPI, configuration par variables d'environnement, connexion PostgreSQL, modèles SQLAlchemy 2 typés |
| Migrations | Alembic, migration `0001` (organisations, équipes, utilisateurs, liaison utilisateurs-équipes, journal d'audit), réversible |
| Authentification | Argon2, JWT en cookie `httpOnly`, connexion / déconnexion / profil, messages identiques pour e-mail inconnu et mauvais mot de passe |
| Rôles | `ADMIN`, `MANAGER`, `AGENT`, `VIEWER`, contrôlés côté API ; isolation par organisation |
| Administration | Utilisateurs (liste, création, modification de rôle, d'équipes, activation), équipes, journal d'audit |
| Données de démonstration | Organisation de démonstration au secteur paramétrable (`DEMO_PROFILE`), 4 équipes, 7 utilisateurs fictifs, script idempotent `python -m app.seed` |
| Frontend | Next.js 15, page de connexion, espace connecté, barre latérale filtrée par rôle, responsive (menu mobile), vue d'ensemble avec état réel de l'API, pages des modules annonçant leur phase, page d'administration |
| Design system | Couleurs (blanc, gris, bleu marine) et composants : bouton, champ, carte, badge, chargement, erreur, état vide |
| Infrastructure | Docker Compose (db, api, web), `.env.example`, CI GitHub Actions (lint, typage, tests, build) |
| Documentation | ADR-001 à 003, matrice rôles / permissions reliée aux tests, Definition of Done, README |

## Tests exécutés

| Contrôle | Résultat |
|---|---|
| `pytest` (base PostgreSQL réelle, migrations descendues puis remontées à chaque run) | 23 tests passés |
| `ruff check`, `ruff format --check` | OK |
| `mypy app` en mode strict | OK, 0 erreur |
| `npm run lint`, `tsc --noEmit` | OK |
| `npm run build` | OK |

Ce que couvrent les tests : connexion et cookie, refus des identifiants invalides avec trace d'audit, jeton falsifié, compte désactivé, déconnexion, permissions de chaque rôle sur chaque route d'administration, isolation entre organisations, protection contre l'auto-retrait des droits, audit des changements de rôle avec valeur avant / après, validation des entrées.

## Décisions prises

- Port de la base sur le poste : **5434**, car un autre PostgreSQL utilise déjà le 5433 sur la machine de développement.
- Tailwind CSS fixé en **4.2.4** : la 4.3 dépend d'un module ESM que Node 20.12 (version du poste) ne sait pas charger. À relever quand Node sera mis à jour (≥ 20.19).
- Types TypeScript de l'API écrits à la main pour l'instant ; génération depuis l'OpenAPI en phase 2, quand les contrats grossiront.
- Pas de tests Playwright en phase 1 : ils arrivent avec le premier parcours métier complet (phase 2).

## Points ouverts

- Limitation des tentatives de connexion : à faire avant tout déploiement public.
- Dépôt GitHub `Meziii/business-operations-hub` à créer par Mehdi ; le dépôt local est initialisé, sans commit.

## Prochaines tâches (phase 2)

1. BPMN AS-IS / TO-BE du traitement des demandes, règles de gestion, critères d'acceptation des stories E1.
2. Modèle : clients et partenaires, catalogue produits (références), catégories, politiques SLA, demandes, événements, commentaires, pièces jointes.
3. Parcours classique complet, puis suggestions IA (interface fournisseur + mode mock) et leur évaluation.

## Compétences mobilisées

- **Business Analysis :** matrice rôles / permissions, Definition of Done, traçabilité exigences → tests (NFR-01, NFR-02, NFR-05, NFR-06, BR-15).
- **Technique :** conception d'API REST, sécurité applicative (hachage, cookies, contrôle d'accès, isolation multi-organisation), migrations de base, typage strict, tests d'intégration sur base réelle, conteneurisation, intégration continue, interface React accessible.
