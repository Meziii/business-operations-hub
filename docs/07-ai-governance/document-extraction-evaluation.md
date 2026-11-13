# Évaluation de l'extraction documentaire

Mesures du 13/11/2026. Reproduire : `cd backend && python -m app.modules.documents.evaluate`
(ou `--split dev`, `--split all`, `--provider claude`). L'OCR exige Tesseract : il tourne dans
l'image Docker et en intégration continue ; sur un poste sans Tesseract, les scans sont comptés à
part (« non évalués ») plutôt que comptés faux.

## Ce qui est évalué

Pour chaque document, on compare les champs extraits aux valeurs attendues (égalité métier : casse
et espaces ignorés pour le texte, au centime près pour les montants) et on vérifie que les anomalies
attendues sont bien détectées. Deux fournisseurs, même interface (`DocumentExtractor`) :

| Fournisseur | Principe | Quand |
|---|---|---|
| `mock-rules-v1` | Règles par libellés, déterministes, sans clé | Mode démonstration et repli automatique |
| `claude:<modèle>` | Modèle de langage, sortie structurée validée | `AI_PROVIDER=claude` + `ANTHROPIC_API_KEY` |

## Jeu de données

40 documents **synthétiques** fabriqués en PDF à partir de leurs valeurs attendues
(`eval/render.py`), puis passés par la vraie chaîne (texte/OCR, extraction, contrôles). Les « scans »
sont des images bruitées et légèrement inclinées, sans couche texte : ils forcent l'OCR.

| Split | Taille | Usage |
|---|---|---|
| `dev` | 20 | Mises en page consultées pour écrire les règles (factures A et B, garanties F et L) |
| `test` | 20 | Jamais utilisées pour régler les règles ; inclut une mise en page **C** (facture en anglais) jamais vue en mise au point |

Chaque split mêle PDF texte et scans, clients standard et premium, et des documents porteurs
d'anomalies (total faux, échéance incohérente, doublon, panne avant achat, hors garantie, champ manquant).

## Résultats — mode démonstration (`mock-rules-v1`)

| Mesure | `dev` | `test` |
|---|---|---|
| Documents entièrement justes | 85 % | **50 %** |
| Exactitude par champ — PDF texte | 100 % | 80 % |
| Exactitude par champ — scans (OCR) | 86 % | 67 % |
| Anomalies détectées | 5/6 | 4/5 |

Exactitude par mise en page (jeu de test) : A, B, F, L (texte) **100 %** ; C (anglais, jamais vue)
**22 %** ; les scans oscillent entre 57 % et 89 % selon la mise en page.

Lecture honnête : les règles lisent **parfaitement les mises en page qu'elles connaissent**, même
scannées à l'OCR, et **s'effondrent sur une mise en page nouvelle** (la facture anglaise, dont les
libellés — « Invoice No. », « Bill to », « Subtotal » — ne figurent dans aucune règle). C'est la
limite attendue d'une approche par libellés, et la raison d'être du jeu de test : sans la mise en
page C, on aurait cru les règles bien plus générales qu'elles ne le sont. C'est la référence à
battre par le modèle de langage.

Les fausses alertes (8 sur le jeu de test) sont presque toutes des **avertissements** non bloquants
(taux de TVA ou dates jugés douteux sur un montant mal lu par l'OCR) : elles envoient un document en
vérification sans le bloquer, ce qui est le comportement voulu.

## Modèle de langage

**Non mesuré à ce jour** : l'évaluation exige une clé API. Commande prête :

```sh
AI_PROVIDER=claude ANTHROPIC_API_KEY=... python -m app.modules.documents.evaluate --provider claude --split test
```

Aucun chiffre ne sera publié pour ce fournisseur avant d'avoir été mesuré sur ce même split `test`.
Référence à battre : 50 % de documents entièrement justes.

## Mesure en conditions réelles

La page « Qualité de l'extraction » (responsables et administrateurs) suit aussi les décisions des
équipes : part des extractions validées sans retouche, corrigées, rejetées, et, champ par champ, la
part conservée telle quelle. Dans la démonstration, ces décisions sont **simulées** par le script de
données (`app/seed_documents.py`) et la page l'indique.

## Garde-fous

| Risque | Mesure | Test |
|---|---|---|
| Extraction appliquée sans contrôle | Décision humaine obligatoire ; validation bloquée tant qu'une anomalie bloquante subsiste | `test_blocking_anomaly_prevents_validation_until_corrected` |
| Valeurs invalides (date, montant) enregistrées | Validation par schéma Pydantic côté serveur, à l'extraction comme à la correction | `test_corrections_are_validated_by_schema` |
| Panne ou délai du fournisseur | Repli automatique sur les règles, signalé « (repli) » | `test_failing_provider_falls_back_to_rules` |
| Document scanné illisible | Importé quand même, saisie manuelle possible, aucune valeur inventée | `test_corrupted_pdf_is_kept_for_manual_entry` |
| Injection d'instruction dans le document | Texte encadré et déclaré comme donnée dans le prompt (NFR-10) | (prompt `claude_extract.py`) |
| Doublons de factures | Clé métier vérifiée, bloquant, référence du document d'origine citée | `test_duplicates_are_blocking` |
| Traçabilité | Chaque version conservée (proposition + corrections), décision au journal d'audit | `test_blocking_anomaly_prevents_validation_until_corrected` |

## Limites de cette évaluation

- Jeu petit (20 documents en `test`) : une erreur de plus ou de moins déplace nettement le score.
- Documents synthétiques fabriqués par la même personne que les règles : plus homogènes que de vrais PDF ; les scores réels seraient probablement plus bas, surtout sur des mises en page variées.
- OCR dépendant de la version de Tesseract : les chiffres des scans peuvent varier légèrement d'une machine à l'autre.
- Une seule valeur attendue par champ, alors que certains libellés réels sont ambigus.
