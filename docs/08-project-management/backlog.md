# Backlog initial

Priorités MoSCoW. Les critères d'acceptation Given / When / Then seront rédigés au début de chaque phase, story par story.

## E0 — Socle (phase 1)

| ID | User story | MoSCoW |
|---|---|---|
| US-001 | En tant qu'utilisateur, je me connecte avec e-mail et mot de passe pour accéder à mon espace | Must |
| US-002 | En tant qu'admin, je crée des utilisateurs, leur rôle et leurs équipes | Must |
| US-003 | En tant qu'utilisateur, je navigue entre les modules depuis une barre latérale commune | Must |
| US-004 | En tant que développeur, je lance toute l'application avec `docker compose up` | Must |
| US-005 | En tant qu'admin, je consulte le journal des actions sensibles | Should |
| US-006 | En tant que démonstrateur, je charge un jeu de données synthétiques reproductible | Must |

## E1 — Demandes, fonctions classiques (phase 2)

| ID | User story | MoSCoW |
|---|---|---|
| US-101 | En tant qu'agent, je crée une demande pour un client ou un partenaire | Must |
| US-102 | En tant qu'agent, je recherche et filtre les demandes (statut, priorité, catégorie, équipe) | Must |
| US-103 | En tant qu'agent, je fais avancer une demande dans son cycle de vie selon les transitions autorisées | Must |
| US-104 | En tant qu'agent, je vois l'échéance SLA et les demandes en retard | Must |
| US-105 | En tant qu'agent, j'ajoute commentaires et pièces jointes | Must |
| US-106 | En tant que responsable, je consulte l'historique complet d'une demande | Must |
| US-107 | En tant que responsable, je vois un tableau de suivi de la charge et des retards de mes équipes | Should |
| US-108 | En tant qu'admin, je gère clients, partenaires, catégories et SLA | Should |
| US-109 | En tant qu'agent, j'importe des demandes depuis un CSV | Could |

## E2 — Demandes, assistance IA (phase 2)

| ID | User story | MoSCoW |
|---|---|---|
| US-201 | En tant qu'agent, je reçois une suggestion de catégorie, priorité et équipe avec explication et confiance | Must |
| US-202 | En tant qu'agent, j'accepte, modifie ou rejette chaque suggestion ; ma décision est tracée | Must |
| US-203 | En tant que responsable, je mesure l'exactitude du classificateur sur un jeu de test étiqueté | Must |
| US-204 | En tant qu'utilisateur, l'application fonctionne en mode démonstration sans clé API | Must |

## E3 — Traitement documentaire (phase 3)

| ID | User story | MoSCoW |
|---|---|---|
| US-301 | En tant qu'agent, j'importe un PDF (facture ou garantie) ; le système vérifie type et taille | Must |
| US-302 | En tant qu'agent, j'obtiens le texte, y compris d'un PDF scanné (OCR) | Must |
| US-303 | En tant qu'agent, je vois les champs extraits, leur confiance et les champs à vérifier | Must |
| US-304 | En tant qu'agent, je suis alerté des champs manquants, doublons et incohérences | Must |
| US-305 | En tant qu'agent, je corrige puis valide ou rejette l'extraction | Must |
| US-306 | En tant qu'agent, je rattache le document à une demande existante | Should |
| US-307 | En tant qu'agent, je traite aussi justificatifs, rapports d'intervention et bons de commande | Could |

## E4 — Assistant de connaissance (phase 4)

| ID | User story | MoSCoW |
|---|---|---|
| US-401 | En tant que responsable, j'importe un document de connaissance et je fixe sa visibilité | Must |
| US-402 | En tant qu'agent, je pose une question et reçois une réponse avec ses sources (document, page) | Must |
| US-403 | En tant qu'agent, l'assistant me dit quand l'information est absente | Must |
| US-404 | En tant qu'agent, je retrouve mes conversations | Should |
| US-405 | En tant qu'agent, je note une réponse (utile / pas utile) | Should |
| US-406 | En tant que responsable, j'exécute le jeu d'évaluation et je vois ses résultats | Must |
| US-407 | En tant qu'agent, j'ajoute une réponse citée en commentaire d'une demande | Could |

## E5 — Cockpit BI (phase 5)

| ID | User story | MoSCoW |
|---|---|---|
| US-501 | En tant que responsable, je vois les KPI des demandes (volumes, SLA, délais, charge) | Must |
| US-502 | En tant que responsable, je vois les KPI documentaires et de l'assistant | Must |
| US-503 | En tant que responsable, je filtre par période, équipe et catégorie | Must |
| US-504 | En tant qu'analyste, je consulte la fiche de chaque KPI (définition, formule, source, fréquence, interprétation) | Must |
| US-505 | En tant qu'analyste, je connecte Power BI aux vues analytiques | Should |
| US-506 | En tant que responsable, je reçois des alertes simples (SLA en dérive, file qui gonfle) | Could |

## E6 — Qualité et portfolio (phase 6)

Recette et rapport, matrice de traçabilité, revue de sécurité, README et captures, script de démonstration. Toutes Must.
