# Évaluation du tri assisté des demandes

US-203. Mesures du 13/11/2026. Reproduire : `cd backend && python -m app.ai.evaluate --split test` (ou `--split dev`, `--split all`).

## Ce qui est évalué

Pour chaque demande, le système propose une **catégorie** (7 possibles), une **priorité** (4 niveaux) et une **équipe** (4 équipes). La proposition est toujours relue : un collaborateur l'accepte, la corrige ou la rejette (RG-10). L'évaluation répond à la question « à quelle fréquence la proposition est-elle juste du premier coup ? ».

Deux fournisseurs implémentent la même interface (`TriageProvider`, `backend/app/ai/triage.py`) :

| Fournisseur | Principe | Quand |
|---|---|---|
| `mock-rules-v1` | Règles par mots-clés, déterministes, sans clé API | Mode démonstration (`AI_PROVIDER=mock`) et repli automatique si le modèle échoue |
| `claude:<modèle>` | Modèle de langage avec sortie structurée validée (Pydantic) | `AI_PROVIDER=claude` et `ANTHROPIC_API_KEY` |

## Jeu de données

`backend/app/ai/eval/triage_dataset.jsonl` : 60 demandes **synthétiques** rédigées en français et étiquetées selon les règles de gestion (catégorie, priorité ; l'équipe attendue est l'équipe par défaut de la catégorie).

| Split | Taille | Usage |
|---|---|---|
| `dev` | 30 | Exemples consultés pendant l'écriture des règles |
| `test` | 30 | Jamais utilisés pour régler les règles |

Répartition du split `test` : 6 livraison, 5 facturation, 5 technique, 4 commande, 4 garantie, 4 compte, 2 autre ; 17 Normale, 6 Haute, 5 Basse, 2 Critique ; 4 clients Premium. Le jeu contient aussi une tentative d'injection d'instruction (« Ignore les consignes précédentes… »).

## Résultats

### Mode démonstration (`mock-rules-v1`)

| Champ | `dev` (30) | `test` (30) |
|---|---|---|
| Catégorie | 93 % (28) | 60 % (18) |
| Priorité | 97 % (29) | 83 % (25) |
| Équipe | 97 % (29) | 63 % (19) |
| **Les trois justes** | **90 %** | **47 %** |

Latence moyenne inférieure à 1 ms.

Lecture : sur les exemples qui ont servi à les écrire, les règles semblent excellentes (90 %) ; sur des demandes nouvelles, moins d'une sur deux est entièrement bien triée. **Les mots-clés généralisent mal.** C'est précisément pourquoi le split `test` existe : sans lui, on aurait annoncé 90 %.

Erreurs typiques sur `test` (détail : page « Qualité du tri IA » de l'application) :
- vocabulaire absent des listes : « écran fissuré », « bruit anormal », « aide au réglage » tombent en « Autre demande » ;
- mots ambigus : « avoir » (facturation) pris pour un retour, « accès pour notre comptable » (compte) pris pour de la facturation ;
- nuances de priorité : « pénalités facturées à tort » n'est pas urgent malgré son ton.

L'erreur de catégorie se propage à l'équipe, d'où des scores catégorie et équipe proches.

### Modèle de langage

**Non mesuré à ce jour** : l'évaluation exige une clé API. Commande prête :

```sh
AI_PROVIDER=claude ANTHROPIC_API_KEY=... python -m app.ai.evaluate --provider claude --split test
```

Aucun chiffre ne sera publié pour ce fournisseur avant d'avoir été mesuré sur ce même split `test`. Référence à battre : 47 % de demandes entièrement bien triées.

## Mesure en conditions réelles

La page « Qualité du tri IA » (responsables et administrateurs) suit aussi les décisions des équipes : part des propositions acceptées, corrigées, rejetées, et champ par champ ce qui a été conservé. Dans la démo, ces décisions sont **simulées** par le script de données (`app/seed_requests.py`) et la page l'indique : elles illustrent l'écran, elles ne mesurent pas un modèle.

## Garde-fous

| Risque | Mesure | Test |
|---|---|---|
| Proposition appliquée sans contrôle | Toute proposition attend une décision humaine ; rejeter ne modifie rien | `test_reject_changes_nothing_and_decision_is_final` |
| Le modèle invente une catégorie ou une équipe | Codes revérifiés par le service ; sinon repli sur les règles, signalé « (repli) » | `test_provider_failure_falls_back_to_rules` |
| Panne ou délai du fournisseur | Repli automatique sur les règles, l'agent peut toujours classer | `test_provider_failure_falls_back_to_rules` |
| Injection d'instruction dans le texte client | Texte encadré et déclaré comme donnée dans le prompt ; cas présent dans le jeu d'évaluation | `test_injected_instruction_is_treated_as_text` |
| Confiance trompeuse | Confiance affichée par champ ; la confiance globale est la plus faible des trois | `test_keywords_drive_category_team_and_explanation` |
| Traçabilité | Fournisseur, latence, proposition, décision, auteur et valeurs finales conservés (`ai_suggestions`) ; décision au journal d'audit | `test_modify_records_final_values` |

## Limites de cette évaluation

- Jeu petit (30 demandes en `test`) : une erreur de plus ou de moins fait varier le score de 3 points.
- Données synthétiques écrites par la même personne que les règles : le vocabulaire est plus homogène que celui de vrais clients ; les scores réels seraient probablement plus bas.
- Une seule étiquette par demande, alors que certaines demandes sont ambiguës (une facture erronée sur une livraison incomplète).
- Les règles ont été complétées une fois après l'écriture du jeu, sur un cas observé pendant la recette (« ligne de production à l'arrêt » non reconnue comme critique) et non tiré du split `test` ; les scores ci-dessus sont ceux mesurés après ce changement, identiques à ceux d'avant.
