# Bilan de la phase 3 — Module 2 : traitement documentaire

Date : 13/11/2026.

## Réalisé

| Livrable | Contenu |
|---|---|
| Analyse | Processus AS-IS / TO-BE, cycle de vie, 8 règles de traitement et 8 contrôles reliés aux tests ([traitement documentaire](../03-processes/document-processing.md)) |
| Modèle | Migration `0003`, réversible : `documents` (référence, type, statut, texte, OCR, clé de doublon, rattachement), `extractions` (versions successives, source IA ou humaine), `anomalies` (recalculées à chaque version) |
| Lecture PDF | Couche texte via pypdfium2 ; bascule automatique sur l'OCR (Tesseract, français) pour les pages scannées ; document illisible conservé pour saisie manuelle |
| Extraction | Interface `DocumentExtractor` ; mode démonstration par libellés (tolérant au bruit d'OCR) ; fournisseur Claude à sortie structurée ; validation par schéma ; repli automatique |
| Contrôles | Champs manquants, total incohérent, taux de TVA inhabituel, échéance douteuse, doublon (clé métier), panne avant achat, hors garantie, date dans le futur ; bloquants vs avertissements |
| Décision humaine | Correction versionnée, validation (bloquée par une anomalie bloquante), rejet motivé, rattachement à une demande ; tout tracé au journal d'audit et dans l'historique de la demande |
| Évaluation | Jeu de 40 documents étiquetés (20 dev, 20 test) fabriqués en PDF, script `python -m app.modules.documents.evaluate`, page « Qualité de l'extraction » ([évaluation](../07-ai-governance/document-extraction-evaluation.md)) |
| Interface | Liste avec indicateurs et filtres, import PDF, détail avec aperçu du PDF, champs éditables et confiance, anomalies, validation / rejet, rattachement, versions ; documents rattachés visibles sur la demande |
| Démonstration | 10 documents rejoués par la vraie chaîne à des dates passées : validés (dont un total corrigé), rejetés, à vérifier (dont un doublon), garanties rattachées à des demandes |
| Documentation | Traitement documentaire, évaluation, droits du module, état réel du modèle de données, README |

## Couverture du backlog

| Story | Priorité | État |
|---|---|---|
| US-301 Import PDF, type et taille vérifiés | Must | Livrée |
| US-302 Texte, y compris OCR des scans | Must | Livrée |
| US-303 Champs extraits, confiance, champs à vérifier | Must | Livrée |
| US-304 Alerte champs manquants, doublons, incohérences | Must | Livrée |
| US-305 Correction puis validation ou rejet | Must | Livrée |
| US-306 Rattachement à une demande | Should | Livrée |
| US-307 Autres types (justificatifs, rapports, bons de commande) | Could | Non faite (deux types au MVP) |

## Tests exécutés

| Contrôle | Résultat |
|---|---|
| `pytest` (base PostgreSQL réelle, migrations descendues puis remontées) | 82 tests passés, 1 sauté hors Docker (65 en phase 2) |
| `ruff check`, `ruff format --check` | OK |
| `mypy app` en mode strict | OK, 0 erreur |
| `npm run lint`, `tsc --noEmit`, `npm run build` | OK |
| Recette manuelle dans le navigateur (Docker, OCR actif) | Liste et indicateurs, détail avec aperçu PDF, doublon bloquant signalé renvoyant au document d'origine, page qualité |

Le test OCR (`test_scanned_document_goes_through_ocr`) est sauté sur un poste sans Tesseract ; il
s'exécute en intégration continue et dans l'image Docker, où Tesseract est installé.

## Décisions prises

- **Bloquant vs avertissement** : seules les anomalies qui remettent en cause la fiabilité (champ obligatoire manquant, total faux, doublon, panne avant achat) interdisent la validation ; les autres (taux de TVA, échéance, hors garantie) alertent sans bloquer.
- **Extraction versionnée** : la proposition de l'IA et chaque correction humaine sont conservées ; on peut toujours voir ce qui a été proposé puis changé.
- **OCR dans l'image, pas sur le poste** : Tesseract est installé dans le conteneur et en CI ; le développement local sans Tesseract fonctionne (saisie manuelle, test OCR sauté).
- **Deux splits d'évaluation**, dont une mise en page jamais vue (facture anglaise) : le score sur les mises en page connues (100 %) n'est jamais présenté seul ; la référence est le jeu de test (50 % de documents entièrement justes).
- **Rapports d'évaluation pré-calculés au démarrage** : l'évaluation hors-ligne fait tourner l'OCR (~1 min) ; elle est calculée une fois en tâche de fond au lancement de l'API pour que la page Qualité réponde vite.

## Défauts trouvés en recette et corrigés

| Constat | Correction |
|---|---|
| Règles d'extraction trop strictes face au bruit d'OCR (préfixes « \| », « _ », deux-points) : scans du jeu dev à 68 % | Nettoyage général du bruit en tête et en fin de valeur (sans retirer la ponctuation d'une vraie phrase) ; scans dev remontés à 86 % |
| Page « Qualité » bloquée ~80 s puis en erreur : l'évaluation OCR tournait dans la requête HTTP | Pré-calcul au démarrage dans un fil d'arrière-plan, résultat mis en cache |

## Points ouverts

- Mesurer le fournisseur Claude sur le split `test` (clé API nécessaire) avant toute communication de résultat.
- US-307 : autres types de documents. Période de garantie paramétrable par produit.
- Repris des phases précédentes : limitation des tentatives de connexion, génération des types TypeScript depuis l'OpenAPI, tests end-to-end Playwright.
- Au premier démarrage de l'API, la page Qualité n'est prête qu'après ~1 min (le temps du pré-calcul OCR) ; un rafraîchissement suffit.

## Prochaine phase (phase 4)

Module 3, assistant de connaissance : réponses aux questions internes depuis la documentation, avec
citation des sources, refus quand l'information manque, et évaluation dédiée.

## Compétences mobilisées

- **Business Analysis :** modélisation AS-IS / TO-BE, règles de traitement et de contrôle numérotées et tracées, cycle de vie, matrice des droits, suivi du backlog, recette.
- **IA appliquée :** chaîne d'extraction documentaire (OCR, extraction structurée, validation par schéma, contrôles métier), « l'IA propose, l'humain décide », protocole d'évaluation avec jeu de test séparé et mise en page inédite, lecture honnête des limites.
- **Technique :** traitement de PDF et OCR, données versionnées, API REST, interface React avec aperçu de document et édition de champs, tests d'intégration sur base réelle, conteneurisation d'une dépendance système (Tesseract), pré-calcul en tâche de fond.
