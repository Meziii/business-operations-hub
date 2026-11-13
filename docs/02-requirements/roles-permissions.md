# Matrice des rôles et permissions

État au 12/11/2026 (phase 1). Les colonnes des modules 1 à 4 seront complétées à leur livraison. Chaque ligne « livrée » est couverte par un test automatisé (`backend/tests/`).

| Action | ADMIN | MANAGER | AGENT | VIEWER | Statut | Test |
|---|:-:|:-:|:-:|:-:|---|---|
| Se connecter, voir son profil | ✔ | ✔ | ✔ | ✔ | Livrée | `test_auth.py` |
| Lister les équipes de son organisation | ✔ | ✔ | ✔ | ✔ | Livrée | `test_teams_list_counts_members` |
| Lister les utilisateurs | ✔ | ✔ | ✘ | ✘ | Livrée | `test_list_users_permissions` |
| Créer un utilisateur | ✔ | ✘ | ✘ | ✘ | Livrée | `test_only_admin_creates_users` |
| Modifier rôle, équipes, activation | ✔ | ✘ | ✘ | ✘ | Livrée | `test_role_change_is_audited_with_before_after` |
| Créer une équipe | ✔ | ✘ | ✘ | ✘ | Livrée | `test_only_admin_creates_teams` |
| Consulter le journal d'audit | ✔ | ✘ | ✘ | ✘ | Livrée | `test_audit_visible_to_admin_only` |

Règles transverses (livrées) :
- Toutes les lectures et écritures sont limitées à l'organisation de l'utilisateur (`test_organizations_are_isolated`).
- Un administrateur ne peut ni se désactiver ni se retirer le rôle ADMIN (`test_admin_cannot_remove_own_rights`).
- Un compte désactivé perd l'accès immédiatement, même avec une session ouverte (`test_deactivated_user_loses_access`).
