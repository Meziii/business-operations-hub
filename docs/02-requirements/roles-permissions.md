# Matrice des rôles et permissions

État au 13/11/2026 (phase 3 : socle, module 1 et module 2). Les modules 3 et 4 seront ajoutés à leur livraison. Chaque ligne « livrée » est couverte par un test automatisé (`backend/tests/`).

| Action | ADMIN | MANAGER | AGENT | VIEWER | Statut | Test |
|---|:-:|:-:|:-:|:-:|---|---|
| Se connecter, voir son profil | ✔ | ✔ | ✔ | ✔ | Livrée | `test_auth.py` |
| Lister les équipes de son organisation | ✔ | ✔ | ✔ | ✔ | Livrée | `test_teams_list_counts_members` |
| Lister les utilisateurs | ✔ | ✔ | ✘ | ✘ | Livrée | `test_list_users_permissions` |
| Créer un utilisateur | ✔ | ✘ | ✘ | ✘ | Livrée | `test_only_admin_creates_users` |
| Modifier rôle, équipes, activation | ✔ | ✘ | ✘ | ✘ | Livrée | `test_role_change_is_audited_with_before_after` |
| Créer une équipe | ✔ | ✘ | ✘ | ✘ | Livrée | `test_only_admin_creates_teams` |
| Consulter le journal d'audit | ✔ | ✘ | ✘ | ✘ | Livrée | `test_audit_visible_to_admin_only` |

### Module 1 : demandes

| Action | ADMIN | MANAGER | AGENT | VIEWER | Statut | Test |
|---|:-:|:-:|:-:|:-:|---|---|
| Consulter les demandes, leur détail et les indicateurs | ✔ | ✔ | ✔ (périmètre RG-11) | ✔ | Livrée | `test_agent_sees_own_teams_and_unrouted_only` |
| Créer une demande | ✔ | ✔ | ✔ | ✘ | Livrée | `test_create_permissions` |
| Classer, affecter, changer le statut, commenter, joindre un PDF | ✔ | ✔ | ✔ (périmètre RG-11) | ✘ | Livrée | `test_full_lifecycle_with_controlled_transitions` |
| Accepter, corriger ou rejeter une proposition de tri | ✔ | ✔ | ✔ (périmètre RG-11) | ✘ | Livrée | `test_viewer_cannot_decide` |
| Consulter la qualité du tri IA | ✔ | ✔ | ✘ | ✘ | Livrée | `test_quality_report_permissions_and_content` |
| Modifier les politiques SLA | ✔ | ✘ | ✘ | ✘ | Livrée | `test_sla_update_is_admin_only_and_audited` |
| Modifier une demande clôturée | ✘ | ✘ | ✘ | ✘ | Livrée | `test_full_lifecycle_with_controlled_transitions` |

### Module 2 : documents

| Action | ADMIN | MANAGER | AGENT | VIEWER | Statut | Test |
|---|:-:|:-:|:-:|:-:|---|---|
| Consulter les documents, leur détail et le PDF | ✔ | ✔ | ✔ | ✔ | Livrée | `test_viewer_reads_but_cannot_act` |
| Importer un PDF (facture, garantie) | ✔ | ✔ | ✔ | ✘ | Livrée | `test_upload_permissions` |
| Corriger les champs, valider ou rejeter | ✔ | ✔ | ✔ | ✘ | Livrée | `test_viewer_reads_but_cannot_act` |
| Rattacher un document à une demande | ✔ | ✔ | ✔ | ✘ | Livrée | `test_link_to_request_is_traced_on_both_sides` |
| Consulter la qualité de l'extraction | ✔ | ✔ | ✘ | ✘ | Livrée | `test_quality_report_permissions` |

Règles transverses (livrées) :
- Toutes les lectures et écritures sont limitées à l'organisation de l'utilisateur (`test_organizations_are_isolated`).
- Un administrateur ne peut ni se désactiver ni se retirer le rôle ADMIN (`test_admin_cannot_remove_own_rights`).
- Un compte désactivé perd l'accès immédiatement, même avec une session ouverte (`test_deactivated_user_loses_access`).
