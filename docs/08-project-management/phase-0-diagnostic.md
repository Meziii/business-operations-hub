# Phase 0 — Diagnostic de l'existant

Date : 12/11/2026.

## 1. Existant

| Élément | Constat | Conséquence |
|---|---|---|
| Application | Aucune application ni dépôt `business-operations-hub` existant | Démarrage à zéro |
| Dépôt `port-folio` (Next.js, TypeScript, shadcn/ui) | Stack frontend déjà pratiquée | Même socle frontend, pour la continuité |
| Dépôt `PlayWright` | Tests de bout en bout déjà pratiqués | Réutilisation de l'approche pour les parcours essentiels |
| Travaux réalisés pour des employeurs | Hors du dépôt | **Aucune réutilisation** : ni données, ni modèles, ni mesures, ni captures |
| Poste de développement | Git, Docker, Node 20, Python 3.13 | Tout tourne en local avec Docker Compose |

## 2. Points de vigilance

1. **Confidentialité.** Les données de démonstration sont générées par script, avec des noms, références et montants inventés et marqués « synthétiques ».
2. **Généricité.** La plateforme modélise une organisation du travail commune à beaucoup d'entreprises B2B, pas une entreprise précise. Le secteur n'est qu'un habillage des données de démonstration (`DEMO_PROFILE`).
3. **Honnêteté du README.** Il ne cite que les technologies réellement utilisées dans le code.
4. **Charge.** Le cahier des charges complet représente plusieurs mois pour une personne seule. Le MVP réduit chaque module à son parcours essentiel.
