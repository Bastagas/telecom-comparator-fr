"""Module de scoring composite pour les offres fibre.

Formule définie dans 00_brief/PHASE_2_PLAN.md (section "Formule du score
composite (Phase 2A)"). Score normalisé sur 10, arrondi à 1 décimale.

Variables et poids
------------------
| Variable                | Poids | Sens     |
|-------------------------|-------|----------|
| Prix mensuel            | 35%   | inversé  |
| Débit descendant        | 25%   | direct   |
| Options incluses        | 15%   | direct   |
| Engagement (mois)       | 10%   | inversé  |
| Frais d'installation    | 10%   | inversé  |
| Bonus techno            |  5%   | seuils   |

Cas limite — `min == max` sur le marché
---------------------------------------
Quand une variable n'a aucune dispersion (typique : un seul opérateur en
BDD en début de Phase 2A, où tout le marché = la seule offre), on renvoie
**7.5/10** par défaut. C'est une valeur "marché de référence neutre" : ni
punitive ni flatteuse, et surtout elle évite que le score d'une offre ne
saute brutalement de NULL à 10 au moment où une 2e offre apparaît avec un
prix plus haut. La barre teal s'affiche correctement (≠ vide) pendant
toute la transition multi-opérateurs.

Recalibrage Phase 2B
--------------------
Une 7e variable "qualité réseau ARCEP" sera ajoutée. Les 6 poids actuels
seront alors repondérés (probablement -10 à -15% redistribués sur la
nouvelle variable).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Poids de la formule (somme = 1.0)
WEIGHTS = {
    "price":      0.35,
    "download":   0.25,
    "options":    0.15,
    "engagement": 0.10,
    "setup":      0.10,
    "tech_bonus": 0.05,
}

# Pondération des catégories d'option
OPTION_CATEGORY_WEIGHTS = {
    "streaming": 1.0,
    "tv":        1.0,
    "storage":   0.5,
    "gaming":    0.5,
    "other":     0.5,
}

NEUTRAL_FALLBACK = 7.5  # cf. docstring


def _normalize(value: float, min_val: float | None, max_val: float | None,
               *, inverted: bool = False) -> float:
    """Normalisation min-max bornée [0, 10]. Renvoie NEUTRAL_FALLBACK si
    min == max ou si une borne est indéfinie."""
    if min_val is None or max_val is None or min_val == max_val:
        return NEUTRAL_FALLBACK
    ratio = (float(value) - float(min_val)) / (float(max_val) - float(min_val))
    if inverted:
        ratio = 1.0 - ratio
    return max(0.0, min(10.0, ratio * 10.0))


def _engagement_score(months: int | None) -> float:
    """0 mois = 10, 12 mois = 5, 24 mois = 0, interpolation linéaire au-delà."""
    m = int(months or 0)
    if m <= 0:
        return 10.0
    if m >= 24:
        return 0.0
    return max(0.0, 10.0 - (m / 24.0) * 10.0)


def _tech_bonus(wifi_standard: str | None, upload_mbps: int | None) -> float:
    """Bonus capé à 10 : Wi-Fi 7 = +5, débit montant ≥ 700 Mbps = +5."""
    bonus = 0.0
    if wifi_standard == "Wi-Fi 7":
        bonus += 5.0
    if (upload_mbps or 0) >= 700:
        bonus += 5.0
    return min(bonus, 10.0)


def compute_score(offer: dict[str, Any], market: dict[str, Any]) -> float:
    """Calcule le score composite d'une offre fibre.

    `offer` doit contenir : monthly_price, commitment_months, setup_fee,
    download_mbps, upload_mbps, wifi_standard, options_weighted (somme
    pré-calculée des poids des options incluses).

    `market` doit contenir : price_min, price_max, download_min,
    download_max, setup_min, setup_max.

    Retourne un float [0.0, 10.0] arrondi à 1 décimale.
    """
    sub = {
        "price":      _normalize(offer["monthly_price"],
                                 market.get("price_min"), market.get("price_max"),
                                 inverted=True),
        "download":   _normalize(offer.get("download_mbps") or 0,
                                 market.get("download_min"), market.get("download_max")),
        "options":    min(float(offer.get("options_weighted") or 0) * 2.0, 10.0),
        "engagement": _engagement_score(offer.get("commitment_months")),
        "setup":      _normalize(offer.get("setup_fee") or 0,
                                 market.get("setup_min"), market.get("setup_max"),
                                 inverted=True),
        "tech_bonus": _tech_bonus(offer.get("wifi_standard"),
                                  offer.get("upload_mbps")),
    }
    total = sum(sub[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(max(0.0, min(10.0, total)), 1)


def compute_market_stats(conn) -> dict[str, Any]:
    """Stats min/max sur les offres fibre actives, pour normalisation."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            MIN(o.monthly_price)  AS price_min,    MAX(o.monthly_price)  AS price_max,
            MIN(fs.download_mbps) AS download_min, MAX(fs.download_mbps) AS download_max,
            MIN(o.setup_fee)      AS setup_min,    MAX(o.setup_fee)      AS setup_max
        FROM offers o
        LEFT JOIN fibre_specs fs ON fs.offer_id = o.id
        WHERE o.is_active = 1 AND o.type = 'fibre'
        """
    )
    return cursor.fetchone() or {}


def recalculate_all_scores(conn) -> int:
    """Recalcule et persiste le score de toutes les offres fibre actives.

    Retourne le nombre d'offres mises à jour.
    """
    market = compute_market_stats(conn)
    cursor = conn.cursor(dictionary=True)

    # Une seule requête : on agrège la somme pondérée des options incluses
    # par offre via un CASE sur la catégorie.
    weights_sql = ", ".join(
        f"WHEN opt.category = '{cat}' THEN {weight}"
        for cat, weight in OPTION_CATEGORY_WEIGHTS.items()
    )
    cursor.execute(
        f"""
        SELECT
            o.id,
            o.monthly_price,
            o.commitment_months,
            o.setup_fee,
            fs.download_mbps,
            fs.upload_mbps,
            fs.wifi_standard,
            COALESCE(SUM(
                CASE
                    WHEN oo.is_included = 1 THEN
                        CASE {weights_sql} ELSE 0.5 END
                    ELSE 0
                END
            ), 0) AS options_weighted
        FROM offers o
        LEFT JOIN fibre_specs   fs ON fs.offer_id = o.id
        LEFT JOIN offer_options oo ON oo.offer_id = o.id
        LEFT JOIN options       opt ON opt.id = oo.option_id
        WHERE o.is_active = 1 AND o.type = 'fibre'
        GROUP BY o.id, fs.download_mbps, fs.upload_mbps, fs.wifi_standard
        """
    )
    rows = cursor.fetchall()

    update_cursor = conn.cursor()
    updated = 0
    for offer in rows:
        score = compute_score(offer, market)
        update_cursor.execute(
            "UPDATE offers SET score = %s WHERE id = %s",
            (score, offer["id"]),
        )
        logger.info("Score offer id=%s : %.1f / 10", offer["id"], score)
        updated += 1
    conn.commit()
    return updated
