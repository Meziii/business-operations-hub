# Roadmap

Durées estimées en semaines de travail à temps plein, pour une personne. À temps partiel (pendant la recherche d'emploi), compter environ le double.

| Phase | Contenu | Durée | Livrables BA produits | Fin de phase = |
|---|---|---|---|---|
| 0 | Discovery et cadrage | fait | Vision, charter, parties prenantes, exigences, architecture, modèle v0, backlog | Validation des décisions ci-dessous |
| 1 | Fondations | 1 sem. | ADR, dictionnaire de données, matrice rôles / permissions, Definition of Done | Connexion, navigation, données synthétiques, `docker compose up`, CI verte |
| 2 | Demandes (classique puis IA) | 2 sem. | BPMN AS-IS / TO-BE du traitement des demandes, règles de gestion, cas d'utilisation, critères d'acceptation | Parcours complet d'une demande, suggestions tracées, évaluation du classificateur |
| 3 | Documents | 1,5 sem. | BPMN du traitement documentaire, règles de contrôle, schémas d'extraction | Facture et garantie extraites, contrôlées, validées, rattachées ; mesure par champ |
| 4 | Assistant | 1,5 sem. | Architecture RAG, politique de sources, mesures anti-injection | Réponses citées, refus corrects, évaluation exécutée |
| 5 | Cockpit | 1 sem. | Fiches KPI, modèle analytique, rapport Power BI | Dashboard intégré et rapport Power BI sur les mêmes vues |
| 6 | Qualité et portfolio | 1 sem. | Cahier et rapport de recette, UAT, traçabilité, README final | Démonstration de 10 minutes rejouable |

**Total : environ 8 semaines à temps plein.**

## Ordre recommandé et pourquoi

1. **Module 1 avant tout.** C'est le cœur métier, il porte les entités partagées (clients, équipes, demandes) dont dépendent les trois autres.
2. **Module 2 ensuite**, car il se rattache aux demandes et réutilise l'interface IA déjà construite.
3. **Module 3** en troisième : il est le plus indépendant, mais il a besoin du socle de documents et de permissions.
4. **Module 4 en dernier**, quand les trois modules produisent des données réelles à mesurer.

Point d'étape possible pour le portfolio dès la fin de la phase 2 : le module 1 seul, documenté, est déjà présentable en entretien.
