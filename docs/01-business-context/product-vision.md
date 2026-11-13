# Vision produit — Business Operations Hub

> Solution générique. Les démonstrations utilisent des données synthétiques, habillées selon un secteur au choix (`DEMO_PROFILE`).

## Vision (format « elevator pitch »)

**Pour** les équipes support, après-vente, commerciales et administratives des entreprises B2B,
**qui** perdent du temps à trier des demandes, ressaisir des documents et chercher l'information dans des procédures dispersées,
**Business Operations Hub** est une plateforme opérationnelle unique
**qui** centralise les demandes, pré-traite les documents, répond aux questions à partir de la documentation interne et mesure la performance,
**contrairement à** un assemblage de boîte mail, tableurs et dossiers partagés,
**notre produit** garde l'humain décisionnaire : l'IA propose, explique et cite ses sources ; un collaborateur valide.

## Contexte

Le projet part d'une organisation du travail qu'on retrouve dans la plupart des entreprises qui vendent des produits référencés à des clients professionnels, quel que soit le secteur (automobile, industrie, matériel médical, informatique…) :
- des **demandes** arrivent chaque jour : commande, livraison, panne, réclamation, garantie, facturation, information produit ;
- des **documents PDF** accompagnent ces demandes : factures, demandes de garantie, justificatifs, rapports d'intervention, bons de commande ;
- les collaborateurs se posent des **questions** sur les procédures : conditions de garantie, délais, règles de retour.

Ce qui compte ici, c'est la façon dont le travail est organisé, pas le secteur. Changer de secteur revient à changer le catalogue de produits et les données de démonstration ; les processus, les règles et l'application restent les mêmes.

## Problématique

| Problème observé (hypothèse de cadrage) | Effet |
|---|---|
| Les demandes arrivent par plusieurs canaux et sont triées à la main | Délai avant prise en charge, mauvaise équipe, demandes oubliées |
| Aucune règle de priorité partagée, SLA non suivis | Clients critiques traités comme les autres |
| Les documents sont lus et ressaisis manuellement | Temps perdu, erreurs de saisie, doublons non détectés |
| La documentation est dispersée et longue | Réponses incohérentes d'un collaborateur à l'autre |
| Pas de vue consolidée | Les responsables pilotent sans chiffres fiables |

## Objectifs métier et indicateurs de réussite

Les cibles sont des **hypothèses à valider**. Les valeurs réelles seront mesurées sur les données synthétiques et les jeux de test ; aucun gain ne sera annoncé sans mesure.

| Objectif | Indicateur | Mesure |
|---|---|---|
| Accélérer la prise en charge | Délai entre création et affectation | Horodatages des événements de demande |
| Respecter les engagements de service | % de demandes résolues dans le SLA | Calcul sur la politique SLA par priorité |
| Fiabiliser le tri | Exactitude du classificateur (catégorie, priorité, équipe) | Jeu de test étiqueté, séparé des données de réglage |
| Réduire la ressaisie | Exactitude par champ de l'extraction documentaire | Jeu de documents synthétiques avec valeurs attendues |
| Fiabiliser les réponses internes | % de réponses avec source ; % de refus corrects sur questions hors documentation | Jeu de questions d'évaluation |
| Garder le contrôle humain | % de suggestions IA acceptées / modifiées / rejetées | Journal des décisions |

## Principes produit

1. **L'humain décide.** Aucune action métier irréversible déclenchée par l'IA.
2. **Expliquer et tracer.** Chaque suggestion porte une explication, un niveau de confiance et un historique.
3. **Fonctionne sans IA.** Sans clé API, l'application reste utilisable ; les fonctions IA passent en mode démonstration déterministe.
4. **Mesurer avant d'affirmer.** Tout chiffre affiché vient des données enregistrées ou d'une évaluation exécutée.
5. **Indépendante du secteur.** Les produits, catégories et documents de connaissance sont des données, pas du code.
