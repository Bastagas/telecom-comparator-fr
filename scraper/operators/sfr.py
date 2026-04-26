"""Scraper SFR — fibre uniquement (Phase 2A).

⚠️  DETTE TECHNIQUE Phase 2C
   La constante `KNOWN_OFFERS` plus bas hardcode le mapping Box → débits/Wi-Fi.
   À remplacer par un parsing dynamique des paragraphes "débit théorique"
   du HTML SFR en Phase 2C, avec fixtures HTML versionnées et tests unitaires
   pour sécuriser les évolutions de la page.

Stratégie d'extraction
----------------------
Le scout 2A.0 a montré que la page sfr.fr/offre-internet/ n'expose qu'un
JSON-LD `BreadcrumbList` (fil d'Ariane), inutilisable pour les produits.
On s'appuie donc sur deux sources stables dans le HTML rendu :

1. **Les mentions légales** (`<b>SFR Premium FIBRE :</b> 45,99€/mois,
   sans engagement`) — texte cadre légal, peu volatile, contient nom +
   prix + engagement par offre.
2. **Un mapping documenté Box → débits/Wi-Fi** dérivé des paragraphes
   "débit théorique" du même HTML. Référence horodatée au 2026-04-26 ;
   à raffiner en Phase 2C avec des fixtures HTML versionnées.

Périmètre Phase 2A
------------------
Seules les offres dont les débits sont *explicitement* présents dans le
HTML sont upsertées : **SFR Premium** (8 Gb/s symétrique) et **SFR Power**
(1 Gb/s descendant). Starter (Box 7) et Power S sont skippés avec un
warning — le HTML formule leurs débits sous forme de fourchettes
ambiguës ("500 Mb/s ou 1 Gb/s"), et le brief impose de ne pas insérer
une ligne avec `download_mbps = NULL`.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from scraper.operators.base import BaseScraper

logger = logging.getLogger(__name__)


# Catalogue connu — vérifié 2026-04-26 dans le HTML rendu de
# sfr.fr/offre-internet/. À raffiner Phase 2C avec fixtures.
KNOWN_OFFERS: list[dict[str, Any]] = [
    {
        "legal_name": "SFR Premium FIBRE",
        "display_name": "SFR Fibre Premium",
        "download_mbps": 8000,
        "upload_mbps": 8000,
        "wifi_standard": "Wi-Fi 7",
        "expected_commitment": 0,
    },
    {
        "legal_name": "SFR Power ADSL/FIBRE/THD",
        "display_name": "SFR Fibre Power",
        "download_mbps": 1000,
        "upload_mbps": 100,  # "50 Mb/s ou 100 Mb/s" — borne haute observée
        "wifi_standard": "Wi-Fi 6",
        "expected_commitment": 12,
    },
]

# Frais d'ouverture observés "sur les offres Box" (fibre).
SETUP_FEE_FIBRE_BOX = 49.0


def _parse_legal_block(html: str, legal_name: str) -> dict[str, Any] | None:
    """Extrait prix mensuel et engagement depuis la ligne mentions légales :

        <b>SFR Premium FIBRE :</b> ... 45,99€/mois, sans engagement ...

    Retourne `{"monthly_price": float, "commitment_months": int}` ou None.
    """
    # On capture jusqu'au prochain <p>/<b>/</p> pour rester dans le bloc.
    pattern = (
        re.escape(legal_name)
        + r"\s*:\s*</b>(.{0,400}?)(?:</p>|<b>)"
    )
    block_match = re.search(pattern, html, re.S | re.I)
    if not block_match:
        return None
    block = block_match.group(1)

    price_match = re.search(r"(\d{1,3}[,.]\d{2})\s*€/mois", block)
    if not price_match:
        return None
    monthly_price = float(price_match.group(1).replace(",", "."))

    if re.search(r"sans\s+engagement", block, re.I):
        commitment = 0
    else:
        eng_match = re.search(r"engagement\s+(\d+)\s+mois", block, re.I)
        if not eng_match:
            return None
        commitment = int(eng_match.group(1))

    return {"monthly_price": monthly_price, "commitment_months": commitment}


class SfrScraper(BaseScraper):
    OPERATOR_SLUG = "sfr"
    BASE_URL = "https://www.sfr.fr/offre-internet/"

    def parse_offers(self, html: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for offer_def in KNOWN_OFFERS:
            parsed = _parse_legal_block(html, offer_def["legal_name"])
            if parsed is None:
                logger.warning(
                    "[sfr] offre %r introuvable dans les mentions légales — skip",
                    offer_def["display_name"],
                )
                continue

            if parsed["commitment_months"] != offer_def["expected_commitment"]:
                logger.warning(
                    "[sfr] %r : engagement attendu %d mois, lu %d mois — on garde la valeur lue",
                    offer_def["display_name"],
                    offer_def["expected_commitment"],
                    parsed["commitment_months"],
                )

            results.append({
                "operator_slug": self.OPERATOR_SLUG,
                "type": "fibre",
                "name": offer_def["display_name"],
                "monthly_price": parsed["monthly_price"],
                "promo_price": None,
                "promo_duration_months": None,
                "commitment_months": parsed["commitment_months"],
                "setup_fee": SETUP_FEE_FIBRE_BOX,
                "source_url": self.BASE_URL,
                "score": None,
                "fibre_specs": {
                    "download_mbps": offer_def["download_mbps"],
                    "upload_mbps": offer_def["upload_mbps"],
                    "technology": "FTTH",
                    "wifi_standard": offer_def["wifi_standard"],
                    "has_tv": True,
                    "tv_channels_count": None,
                    "has_landline": True,
                },
            })

        if not results:
            logger.warning("[sfr] aucune offre extraite — la page a peut-être changé")
        return results
