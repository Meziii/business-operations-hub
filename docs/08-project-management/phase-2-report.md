# Bilan de la phase 2 — Module 1 : gestion des demandes

Date : 13/11/2026.

## Réalisé

| Livrable | Contenu |
|---|---|
| Analyse | Processus AS-IS / TO-BE, cycle de vie, 12 règles de gestion reliées aux tests ([traitement des demandes](../03-processes/request-handling.md)) |
| Modèle | Migration `0002`, réversible : clients et partenaires (niveau Standard / Premium), catégories avec équipe par défaut, politiques SLA par priorité, demandes, historique, commentaires, pièces jointes, suggestions IA |
| API | Création, liste filtrée et paginée (statut, priorité, catégorie, équipe, affectation, retard, recherche), détail, modification, transitions contrôlées, commentaires, pièces jointes PDF, indicateurs et charge par équipe, politiques SLA (admin) |
| Tri assisté | Interface `TriageProvider` ; mode démonstration à base de règles (sans clé) ; fournisseur Claude à sortie structurée ; revérification des codes proposés ; repli automatique sur les règles en cas d'échec ; décision humaine obligatoire et tracée |
| Évaluation | Jeu de 60 demandes étiquetées (30 `dev`, 30 `test`), script `python -m app.ai.evaluate`, page « Qualité du tri IA » ([évaluation](../07-ai-governance/triage-evaluation.md)) |
| Interface | Liste avec indicateurs cliquables et filtres dans l'URL, charge des équipes (responsables), création, détail avec proposition de tri, classement et affectation, historique, commentaires, pièces jointes, état SLA ; vue d'ensemble alimentée par les indicateurs réels |
| Démonstration | 10 clients et partenaires, 60 demandes rejouées avec les vraies règles de gestion à des dates passées : 8 à classer, des demandes en cours surtout dans les délais, quelques retards, un historique majoritairement résolu |
| Documentation | Règles de gestion, évaluation du tri, matrice des droits du module, état réel du modèle de données, README |

## Couverture du backlog

| Story | Priorité | État |
|---|---|---|
| US-101 Créer une demande | Must | Livrée |
| US-102 Rechercher et filtrer | Must | Livrée |
| US-103 Cycle de vie contrôlé | Must | Livrée |
| US-104 Échéances SLA et retards | Must | Livrée |
| US-105 Commentaires et pièces jointes | Must | Livrée |
| US-106 Historique complet | Must | Livrée |
| US-107 Charge et retards des équipes | Should | Livrée |
| US-108 Gérer clients, catégories et SLA | Should | **Partielle** : politiques SLA modifiables par l'API (admin, audité) ; clients et catégories chargés par le jeu de démonstration, sans écran de gestion |
| US-109 Import CSV | Could | Non faite |
| US-201 Suggestion avec explication et confiance | Must | Livrée |
| US-202 Accepter, corriger, rejeter, avec trace | Must | Livrée |
| US-203 Mesurer l'exactitude sur un jeu étiqueté | Must | Livrée pour le mode démonstration ; **modèle de langage non mesuré** (clé API nécessaire) |
| US-204 Fonctionner sans clé API | Must | Livrée |

## Tests exécutés

| Contrôle | Résultat |
|---|---|
| `pytest` (base PostgreSQL réelle, migrations descendues puis remontées à chaque run) | 58 tests passés (23 en phase 1) |
| `ruff check`, `ruff format --check` | OK |
| `mypy app` en mode strict | OK, 0 erreur |
| `npm run lint`, `tsc --noEmit`, `npm run build` | OK |
| Recette manuelle dans le navigateur (Docker Compose) | Parcours agent de bout en bout : acceptation et correction d'une proposition, affectation, prise en charge, résolution (bloquée sans commentaire), pièce jointe PDF acceptée et faux PDF refusé, création d'une demande Premium critique. Parcours responsable : charge des équipes, filtres par équipe et catégorie, qualité du tri. Direction : lecture seule vérifiée. Agent refusé sur la page qualité |

Ce que couvrent les nouveaux tests : référence séquentielle, permissions de chaque rôle, validation des entrées et isolation entre organisations, acceptation / correction / rejet et caractère définitif de la décision, affectation limitée aux membres de l'équipe, cycle de vie complet avec transitions refusées et commentaires obligatoires, réouverture, historique avant / après, visibilité d'un agent, filtres et indicateurs, règles d'état SLA, pièces jointes (type vérifié sur le contenu, taille, empreinte), repli quand le fournisseur échoue ou invente un code, règles de priorité dont le relèvement Premium, injection d'instruction, reproductibilité de l'évaluation, cohérence et crédibilité du jeu de démonstration.

## Défauts trouvés en recette et corrigés

| Constat | Correction |
|---|---|
| Badge « En retard » affichant « dans 12 heures » : la prise en charge était dépassée mais l'échéance montrée était celle de la résolution, encore à venir | Un retard s'affiche « En retard » tant que l'échéance montrée n'est pas elle-même dépassée |
| Vue d'ensemble annonçant encore « Demandes : prévu en phase 2 », et badge IA affichant le nom technique du fournisseur | Indicateurs réels du module ; libellé « Mode démonstration (règles) » |
| « Toute la ligne de production est à l'arrêt » proposé en priorité Haute au lieu de Critique | Règle élargie à « à l'arrêt » (cas observé en recette, pas tiré du split `test` ; scores inchangés) et test ajouté |
| Jeu de démonstration : toutes les demandes ouvertes routées en retard dès le chargement, demandes « à classer » vieilles de près de 3 jours | Scénario revu (demandes du jour à classer, travail en cours récent, quelques dossiers oubliés) et test de crédibilité ajouté |
| Filtre par catégorie prévu par US-102 présent dans l'API mais absent de l'écran | Filtre ajouté et testé côté API |
| Pièces jointes impossibles dans Docker (« Envoi impossible ») : l'utilisateur non privilégié du conteneur ne pouvait pas créer le dossier de stockage. Les tests, lancés hors conteneur, ne le voyaient pas | Dossier créé dans l'image avec les bons droits et monté sur un volume `uploads` (fichiers conservés entre deux reconstructions) |
| Explication du tri affichant les mots sans accents (« a l'arret ») et les codes techniques (« CRITICAL ») | Mots cités tels qu'écrits par le client, priorités en français ; test ajouté |

## Décisions prises

- **Décision humaine obligatoire** : aucune proposition n'est appliquée automatiquement, même avec une confiance élevée. La mesure en conditions réelles (part acceptée telle quelle) dira plus tard si un seuil d'application automatique serait défendable.
- **Confiance globale = la plus faible des trois** : une proposition n'est pas plus fiable que son champ le moins sûr.
- **Deux splits d'évaluation** : le score sur les exemples ayant servi à écrire les règles (90 %) n'est jamais présenté seul ; le chiffre de référence est celui du split `test` (47 %).
- **SLA en minutes calendaires**, échéances copiées sur la demande : une modification de politique ne réécrit pas les engagements passés.
- **Mode démonstration conservé comme repli** du modèle de langage : le service reste utilisable en cas de panne ou de réponse invalide.

## Points ouverts

- Mesurer le fournisseur Claude sur le split `test` (clé API nécessaire) avant toute communication de résultat.
- US-108 : écrans d'administration des clients, catégories et politiques SLA. US-109 : import CSV.
- Repris de la phase 1 : limitation des tentatives de connexion, génération des types TypeScript depuis l'OpenAPI, tests end-to-end Playwright sur le parcours de tri.
- Une base de démonstration vieillit avec le temps (les échéances finissent par passer). Pour la régénérer sans toucher aux comptes : vider les tables du module (`accounts`, `categories`, `sla_policies`, `requests` et dépendantes) puis relancer `python -m app.seed`.

## Prochaine phase (phase 3)

Module 2, traitement documentaire : import de factures et demandes de garantie en PDF, extraction des champs avec confiance, contrôles et anomalies, rattachement aux demandes.

## Compétences mobilisées

- **Business Analysis :** modélisation AS-IS / TO-BE, règles de gestion numérotées et reliées aux tests, cycle de vie et matrice des droits, priorisation MoSCoW et suivi de couverture du backlog, recette fonctionnelle.
- **IA appliquée :** conception d'une assistance « l'IA propose, l'humain décide », sortie structurée validée, protection contre l'injection d'instruction, repli, protocole d'évaluation avec jeu de test séparé, lecture honnête des résultats.
- **Technique :** API REST filtrée et paginée, machine à états, calcul SLA, historique d'audit, téléversement sécurisé, migrations réversibles, typage strict, tests d'intégration sur base réelle, interface React avec états de chargement, d'erreur et vide.
