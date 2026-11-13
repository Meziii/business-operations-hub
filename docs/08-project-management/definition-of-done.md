# Definition of Done

Une user story est terminée quand :

1. Ses critères d'acceptation (Given / When / Then) sont vérifiés par au moins un test automatisé.
2. Les permissions sont contrôlées côté API et la matrice [rôles et permissions](../02-requirements/roles-permissions.md) est à jour.
3. Les actions sensibles qu'elle introduit sont écrites dans le journal d'audit.
4. Les contrôles passent : `ruff check`, `ruff format --check`, `mypy app` (strict), `pytest`, `npm run lint`, `tsc --noEmit`, `npm run build`.
5. Toute évolution du schéma passe par une migration Alembic réversible (upgrade et downgrade testés).
6. L'interface traite les états de chargement, d'erreur et vide.
7. La documentation concernée (exigences, modèle de données, ADR) décrit ce qui existe réellement.
8. Aucun secret, aucune donnée réelle : seulement des données synthétiques.
