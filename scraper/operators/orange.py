"""Scraper Orange — fibre uniquement (Phase 2A).

Stratégie d'extraction
----------------------
La page boutique.orange.fr/internet/offres-fibre n'expose ni JSON-LD Product
(uniquement des microdata `schema.org/FAQPage` orientées SAV) ni de store
Next.js. En revanche, un script inline contient `const dto = {...};` (~104 KB),
un objet **JSON natif** parseable directement par `json.loads`, qui contient
tous les champs structurés requis :

    dto["offers"][i] :
      - name, offerSeoId
      - price.{price, initialPrice, duration, priceDetails}
      - attributes[*].description : débits, Wi-Fi, chaînes TV, décodeur
      - banner : "Exclu web : 49€ de frais de mise en service offerts"

Extraction 100 % JSON natif — la voie la plus propre des 4 scrapers Phase 2A
(zéro regex ad hoc côté store, le parsing reste limité aux strings de
description où le designer Orange utilise un format texte structuré).

Règle de scope (cf. JOURNAL Tâche 2A.7)
---------------------------------------
3 offres core retenues : `Livebox Classic`, `Livebox Up`, `Livebox Max`.
Exclues les offres **conditionnées** :
- Série Spéciale Lite (promo limitée temporellement)
- Cheat_Code 18-26 (ciblage étudiant)
- Variantes "+ Smart TV" (bundles redondants, la TV est déjà détectée
  via attributes pour les 3 core).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from scraper.operators.base import BaseScraper

logger = logging.getLogger(__name__)


# Tarif officiel Orange (banner "Exclu web : 49€ de frais offerts").
# La promo offre les frais — non capté par le schéma actuel,
# cf. dette technique `setup_fee_waived` dans JOURNAL (Phase 2C).
SETUP_FEE_FTTH_LIVEBOX = 49.0

# offerSeoId des 3 offres core retenues (catalogue commercial standard).
CORE_SEO_IDS: set[str] = {
    "livebox-classic-fibre",
    "livebox-up-fibre",
    "livebox-max-fibre",
}


def _find_dto_json(html: str) -> str:
    """Trouve le script qui contient `const dto = {...}` et retourne son JSON brut."""
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    for s in scripts:
        m = re.search(r"const\s+dto\s*=\s*({.+})", s, re.S)
        if not m:
            continue
        # Vérifie que c'est du JSON valide (et pas un faux positif).
        try:
            json.loads(m.group(1))
            return m.group(1)
        except json.JSONDecodeError:
            continue
    raise ValueError(
        "DTO Orange introuvable : aucun <script> ne contient un "
        "'const dto = {...}' parseable. La page a peut-être changé."
    )


def _strip_html(s: str | None) -> str:
    return re.sub(r"<[^>]+>", " ", s or "")


def _parse_rate(s: str) -> int | None:
    """'8 Gbit/s' / '900 Mbit/s' / '1 Gb/s' → Mbps. None si illisible."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(G|M)b(?:it)?\s*/?\s*s?\b", s or "", re.I)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    return int(round(value * 1000)) if m.group(2).upper() == "G" else int(round(value))


def _extract_speeds(attributes: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    """Cherche '↓ X Gbit/s ... ↑ Y Gbit/s' dans les attributes.description."""
    for attr in attributes or []:
        desc = _strip_html(attr.get("description"))
        m = re.search(
            r"[↓⬇]\s*([\d.,]+\s*[GM]b(?:it)?\s*/?\s*s?)"
            r".{0,40}?"
            r"[↑⬆]\s*([\d.,]+\s*[GM]b(?:it)?\s*/?\s*s?)",
            desc,
            re.I | re.S,
        )
        if m:
            return _parse_rate(m.group(1)), _parse_rate(m.group(2))
    return None, None


def _extract_wifi_standard(attributes: list[dict[str, Any]]) -> str | None:
    """Cherche 'Wifi N' ou 'WiFi N' dans les attributes.description."""
    for attr in attributes or []:
        desc = _strip_html(attr.get("description"))
        m = re.search(r"Wi[-\s]?Fi\s*(\d+)", desc, re.I)
        if m:
            return f"Wi-Fi {m.group(1)}"
    return None


def _has_tv(attributes: list[dict[str, Any]]) -> bool:
    for attr in attributes or []:
        desc = _strip_html(attr.get("description"))
        if re.search(r"cha[iî]nes?\s+TV|D[eé]codeur\s+TV", desc, re.I):
            return True
    return False


def _commitment_months(price_details: str | None) -> int:
    if not price_details:
        return 0
    if re.search(r"sans\s+engagement", price_details, re.I):
        return 0
    m = re.search(r"engagement\s+(\d+)\s+mois", price_details, re.I)
    return int(m.group(1)) if m else 0


class OrangeScraper(BaseScraper):
    OPERATOR_SLUG = "orange"
    BASE_URL = "https://boutique.orange.fr/internet/offres-fibre"

    def parse_offers(self, html: str) -> list[dict[str, Any]]:
        dto = json.loads(_find_dto_json(html))

        results: list[dict[str, Any]] = []
        for offer in dto.get("offers", []):
            seo_id = offer.get("offerSeoId")
            if seo_id not in CORE_SEO_IDS:
                continue

            name = offer.get("name") or seo_id
            price = offer.get("price") or {}

            promo_price_raw = price.get("price")
            initial_price = price.get("initialPrice")
            if initial_price is None or promo_price_raw is None:
                logger.warning("[orange] %r : prix manquant — skip", name)
                continue

            initial_price = float(initial_price)
            promo_price_raw = float(promo_price_raw)

            # Vraie promo si price < initialPrice ; sinon prix unique.
            if promo_price_raw < initial_price:
                actual_promo_price: float | None = promo_price_raw
                actual_promo_duration = price.get("duration") or None
            else:
                actual_promo_price = None
                actual_promo_duration = None

            commitment = _commitment_months(price.get("priceDetails"))

            attributes = offer.get("attributes") or []
            download_mbps, upload_mbps = _extract_speeds(attributes)
            if download_mbps is None or upload_mbps is None:
                logger.warning(
                    "[orange] %r : débits introuvables dans attributes — skip", name,
                )
                continue

            wifi_standard = _extract_wifi_standard(attributes)
            has_tv = _has_tv(attributes)

            results.append({
                "operator_slug": self.OPERATOR_SLUG,
                "type": "fibre",
                "name": name.strip(),
                "monthly_price": initial_price,
                "promo_price": actual_promo_price,
                "promo_duration_months": actual_promo_duration,
                "commitment_months": commitment,
                "setup_fee": SETUP_FEE_FTTH_LIVEBOX,
                "source_url": self.BASE_URL,
                "score": None,
                "fibre_specs": {
                    "download_mbps": download_mbps,
                    "upload_mbps": upload_mbps,
                    "technology": "FTTH",
                    "wifi_standard": wifi_standard,
                    "has_tv": has_tv,
                    "tv_channels_count": None,
                    "has_landline": True,
                },
            })

        if not results:
            logger.warning("[orange] aucune offre extraite — la page a peut-être changé")
        return results
