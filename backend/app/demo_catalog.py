"""Paramétrage du module Demandes pour l'organisation de démonstration (données synthétiques).

Partagé par le seed et l'évaluation du classificateur : les deux utilisent les mêmes catégories.
"""

from app.models import AccountTier, AccountType, Priority

# code, nom, description, équipe par défaut
CATEGORIES: list[tuple[str, str, str, str]] = [
    (
        "DELIVERY",
        "Livraison et suivi",
        "Retards, colis manquants, suivi d'expédition, adresse de livraison.",
        "SUPPORT",
    ),
    (
        "ORDER",
        "Devis et commande",
        "Devis, prix, disponibilité, passage ou modification de commande.",
        "SALES",
    ),
    (
        "BILLING",
        "Facturation et paiement",
        "Factures, avoirs, paiements, relances, erreurs de montant.",
        "ADMIN_FIN",
    ),
    (
        "WARRANTY",
        "Garantie et retour",
        "Produit défectueux ou endommagé, retour, échange, prise sous garantie.",
        "AFTER_SALES",
    ),
    (
        "TECHNICAL",
        "Assistance technique",
        "Installation, configuration, panne d'utilisation, codes erreur.",
        "AFTER_SALES",
    ),
    (
        "ACCOUNT",
        "Compte et accès",
        "Accès au portail, identifiants, coordonnées, utilisateurs du compte.",
        "SUPPORT",
    ),
    ("OTHER", "Autre demande", "Demande ne relevant d'aucune autre catégorie.", "SUPPORT"),
]

# priorité : (prise en charge, résolution) en minutes calendaires
SLA: dict[Priority, tuple[int, int]] = {
    Priority.CRITICAL: (60, 8 * 60),
    Priority.HIGH: (4 * 60, 24 * 60),
    Priority.MEDIUM: (8 * 60, 3 * 24 * 60),
    Priority.LOW: (24 * 60, 5 * 24 * 60),
}

ACCOUNTS: list[tuple[str, AccountType, AccountTier]] = [
    ("Atelier Morel SARL", AccountType.CUSTOMER, AccountTier.STANDARD),
    ("Batiservices Ouest", AccountType.CUSTOMER, AccountTier.PREMIUM),
    ("Distrinord Partenaires", AccountType.PARTNER, AccountTier.PREMIUM),
    ("Ets Lambert & Fils", AccountType.CUSTOMER, AccountTier.STANDARD),
    ("Groupe Valmont Industrie", AccountType.CUSTOMER, AccountTier.PREMIUM),
    ("Maintenance Express 69", AccountType.CUSTOMER, AccountTier.STANDARD),
    ("Réseau Sud Distribution", AccountType.PARTNER, AccountTier.STANDARD),
    ("Techniparc Services", AccountType.CUSTOMER, AccountTier.STANDARD),
    ("Comptoir Alpin Pro", AccountType.PARTNER, AccountTier.STANDARD),
    ("Hôtellerie Bellevue", AccountType.CUSTOMER, AccountTier.STANDARD),
]
