# Architecture Decision Records

Format court : contexte, décision, conséquences. Une décision remplacée n'est pas supprimée, elle passe au statut « Remplacée par ADR-xxx ».

## ADR-001 — Monolithe modulaire

- **Statut :** acceptée (12/11/2026)
- **Contexte :** une personne, quatre modules qui partagent utilisateurs, équipes, demandes et audit ; volume de démonstration modeste.
- **Décision :** une seule API FastAPI découpée en `app/modules/<module>/`, un seul frontend Next.js, une seule base.
- **Conséquences :** un déploiement, des transactions simples, pas de réseau entre services. Règle : un module n'importe pas les modèles d'un autre module sans passer par une fonction de service explicite, pour garder les frontières nettes.

## ADR-002 — PostgreSQL 16 + pgvector

- **Statut :** acceptée
- **Contexte :** données transactionnelles, indicateurs analytiques et recherche vectorielle (module 3).
- **Décision :** une seule base PostgreSQL, extension `vector`, image `pgvector/pgvector:pg16`.
- **Conséquences :** pas de base vectorielle séparée à exploiter ; les vues analytiques et Power BI lisent la même source.

## ADR-003 — Authentification gérée par l'API

- **Statut :** acceptée
- **Contexte :** les droits doivent être contrôlés là où sont les données (NFR-01).
- **Décision :** mots de passe hachés en Argon2 ; JWT signé (HS256) dans un cookie `httpOnly`, `SameSite=Lax`, `Secure` en production. Le frontend appelle `/api/*` sur sa propre origine (réécriture Next.js vers l'API), donc le cookie reste first-party.
- **Conséquences :** pas de NextAuth à synchroniser, pas de jeton accessible au JavaScript. Le middleware Next.js ne fait qu'une redirection d'ergonomie ; la vérification réelle est faite par l'API à chaque appel. Pas de révocation individuelle des jetons avant expiration (8 h) : un compte désactivé est refusé immédiatement car l'API relit l'utilisateur à chaque requête.
- **Limite connue :** pas encore de limitation du nombre de tentatives de connexion (prévu avant tout déploiement public).

## ADR à rédiger dans les phases suivantes

ADR-004 interface fournisseur IA et mode mock (phase 2) · ADR-005 RAG sans framework (phase 4) · ADR-006 embeddings locaux (phase 4) · ADR-007 traitements asynchrones légers (phase 3) · ADR-008 vues analytiques partagées dashboard / Power BI (phase 5).
