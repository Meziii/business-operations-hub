# Business Requirements (v0)

Identifiants stables : ils serviront à la matrice de traçabilité exigences / tests (phase 6).

## Exigences métier

| ID | Exigence | Module | Priorité |
|---|---|---|---|
| BR-01 | Toute demande est enregistrée dans un référentiel unique, avec client ou partenaire, catégorie, priorité, équipe, statut et dates clés | 1 | Must |
| BR-02 | Le cycle de vie suit 7 statuts (`NEW`, `CLASSIFIED`, `ASSIGNED`, `IN_PROGRESS`, `WAITING_INFO`, `RESOLVED`, `CLOSED`) avec transitions contrôlées | 1 | Must |
| BR-03 | Chaque priorité a un délai de prise en charge et de résolution (SLA) ; les dépassements sont visibles | 1 | Must |
| BR-04 | Toute modification d'une demande est historisée (qui, quoi, quand, avant / après) | 1 | Must |
| BR-05 | Le système propose catégorie, priorité et équipe avec explication et confiance ; un collaborateur accepte, modifie ou rejette | 1 | Must |
| BR-06 | Un PDF importé est converti en texte, y compris s'il est scanné | 2 | Must |
| BR-07 | Les champs clés (références, dates, montants, fournisseur / client) sont extraits dans un format validé par schéma | 2 | Must |
| BR-08 | Les champs manquants, doublons et incohérences sont signalés avant validation | 2 | Must |
| BR-09 | Un document validé peut être rattaché à une demande | 2 | Should |
| BR-10 | Un collaborateur pose une question en langage naturel et reçoit une réponse issue de la documentation, avec ses sources | 3 | Must |
| BR-11 | Si l'information est absente ou insuffisante, l'assistant le dit au lieu d'inventer | 3 | Must |
| BR-12 | Un collaborateur ne voit que les documents de connaissance autorisés pour son rôle | 3 | Must |
| BR-13 | Les responsables consultent des KPI calculés depuis les données enregistrées, filtrables par période, équipe, catégorie | 4 | Must |
| BR-14 | Les données analytiques sont exploitables dans Power BI | 4 | Should |
| BR-15 | Les actions sensibles (validation, rejet, changement de droits, suppression) sont journalisées | Socle | Must |

## Exigences non fonctionnelles

| ID | Exigence |
|---|---|
| NFR-01 | Contrôle des permissions côté backend sur chaque endpoint |
| NFR-02 | Aucun secret dans le dépôt ; configuration par variables d'environnement |
| NFR-03 | Fichiers importés : PDF uniquement, taille maximale configurable (10 Mo par défaut), type vérifié sur le contenu et pas seulement l'extension |
| NFR-04 | Sans fournisseur d'IA configuré, toutes les fonctions classiques fonctionnent et l'IA passe en mode démonstration |
| NFR-05 | Lancement local complet par `docker compose up` |
| NFR-06 | API documentée (OpenAPI) et validée (Pydantic) |
| NFR-07 | Interface responsive, états de chargement, d'erreur et vides traités |
| NFR-08 | Tests automatisés exécutés en intégration continue |
| NFR-09 | Données personnelles minimisées ; données de démonstration marquées synthétiques |
| NFR-10 | Contenu des documents importés jamais interprété comme instruction par l'IA |
