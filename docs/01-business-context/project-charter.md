# Project Charter

## Objet

Construire une application web fonctionnelle et sa documentation d'analyse, pour démontrer une démarche complète : besoin métier → processus cible → spécifications → architecture → développement → recette → pilotage.

## Périmètre MVP

| Module | Inclus dans le MVP | Version simplifiée assumée |
|---|---|---|
| Socle | Connexion, 4 rôles, une organisation de démonstration, équipes, journal d'audit, navigation commune | Une seule organisation active (le modèle reste multi-organisation) |
| 1. Smart Request Management | Création, liste, recherche, filtres, fiche demande, 7 statuts, 4 priorités, SLA par priorité, commentaires, pièces jointes, historique, suggestion IA (catégorie, priorité, équipe, explication, confiance) à accepter / modifier / rejeter, tableau de suivi | Saisie via formulaire et import CSV ; pas de réception d'e-mails |
| 2. Intelligent Document Processing | Import PDF, extraction texte, OCR des scans, extraction structurée validée par schéma, contrôles (champs obligatoires, doublons, incohérences), rattachement à une demande, validation humaine, historique | **Deux types** au MVP : factures et demandes de garantie. Les trois autres types arrivent en évolution |
| 3. Enterprise Knowledge Assistant | Import PDF, découpage, embeddings, recherche vectorielle (pgvector), réponses avec citations, refus si l'information manque, historique des conversations, avis utilisateur, jeu d'évaluation | Permissions par niveau de visibilité du document (tous / équipe / responsables) |
| 4. BI Cockpit | Vues analytiques SQL, ~15 KPI documentés, dashboard intégré avec filtres, export pour Power BI | Rafraîchissement à la demande ; un rapport Power BI construit sur les mêmes vues |

## Hors périmètre (MVP)

Réception des e-mails et canaux externes, SSO / Active Directory, notifications temps réel, application mobile, intégration ERP réelle, apprentissage ou fine-tuning de modèles, multi-langue de l'interface, déploiement public (étudié en phase 6 selon le coût).

## Hypothèses

- Interface en français ; code, base de données et API en anglais (codes de statut `NEW`, `IN_PROGRESS`… avec libellés français).
- Fournisseur d'IA : Claude (Anthropic) derrière une interface ; un mode « mock » déterministe fonctionne sans clé.
- Volume de démonstration : quelques milliers de demandes, une centaine de documents, une vingtaine de documents de connaissance. Cela ne justifie ni file de messages ni microservices.
- Réalisation par une seule personne, avec revue à chaque fin de phase.

## Contraintes

- Données exclusivement synthétiques, générées par script reproductible.
- Aucune clé ni secret dans le dépôt (`.env.example` uniquement).
- Coût d'exploitation proche de zéro : tout tourne en local avec Docker.
- Code et documentation cohérents : un document ne décrit que ce qui existe.

## Risques principaux

| Risque | Impact | Réponse |
|---|---|---|
| Périmètre trop large | Projet jamais terminé | MVP par module, une phase validée avant la suivante |
| Qualité OCR variable | Extraction peu fiable | Champs à faible confiance envoyés en vérification humaine ; mesure sur jeu de test |
| Hallucinations du RAG | Réponses inventées | Réponse uniquement à partir des extraits récupérés, citations obligatoires, seuil de pertinence, refus explicite |
| Injection de prompt via documents importés | Détournement de l'assistant | Documents traités comme données, séparés des instructions ; tests dédiés |
| Ressemblance avec un ancien employeur | Fuite d'information confidentielle | Règle de conception de zéro (cf. diagnostic) |
