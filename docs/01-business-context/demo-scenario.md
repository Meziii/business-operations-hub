# Scénario de démonstration

> Les organisations, personnes, produits et documents de démonstration sont fictifs et synthétiques.

## Une organisation du travail, plusieurs habillages

La plateforme modélise un fonctionnement commun aux entreprises B2B qui vendent des produits référencés : une équipe support reçoit les demandes, un service après-vente traite pannes, réclamations et garanties, une équipe commerciale suit les commandes, une équipe administrative traite factures et bons de commande, et des responsables pilotent l'ensemble.

Le secteur n'est qu'un habillage. Il se choisit avec la variable `DEMO_PROFILE` (fichier `backend/app/demo_profiles.py`) :

| Profil | Organisation de démo | Exemple de produits |
|---|---|---|
| `generic` | Démo — Distribution B2B | Produits multi-catégories référencés |
| `automotive` | Démo — Équipementier automobile | Produits et accessoires automobiles |
| `industrial` | Démo — Fournitures industrielles | Équipements et consommables industriels |

À partir de la phase 2, chaque profil apportera aussi son catalogue de produits (référence, libellé, famille), ses catégories de demandes et ses documents de connaissance. Les équipes, les rôles, les statuts, les SLA et les écrans restent identiques.

## Flux traités

| Flux | Émetteur | Équipe destinataire |
|---|---|---|
| Demandes d'information, de commande, de livraison | Clients, partenaires | Support, commercial |
| Pannes, réclamations et demandes de garantie, avec pièces jointes | Clients, partenaires | Après-vente |
| Factures, bons de commande, justificatifs | Fournisseurs, clients | Administration |
| Rapports d'intervention | Techniciens, partenaires | Après-vente |
| Questions sur les procédures internes | Collaborateurs | Tous |

## Situation de départ (AS-IS, résumé)

Les demandes arrivent par e-mail, téléphone et formulaires, puis sont triées à la main. Les documents PDF sont lus et ressaisis. Les procédures (garantie, retours, délais) sont dispersées dans des dossiers partagés. Les responsables consolident les chiffres dans des tableurs.

Le détail des processus AS-IS et TO-BE sera modélisé en BPMN au début de chaque module (`docs/03-processes/`).
