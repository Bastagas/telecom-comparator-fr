"""Scraper Bouygues — fibre uniquement (Phase 2A).

Stratégie d'extraction
----------------------
La page bouyguestelecom.fr/offres-internet n'expose pas de JSON-LD Product
(uniquement un BreadcrumbList) ni de microdata. En revanche, un script
Next.js inline (~178 KB, identifié par la cooccurrence des champs
`downRates` et `rangeNg`) contient le **store complet** des offres FAI
avec tous les champs structurés requis :

    name, categories, technology, downRates, upRates,
    details.price.{initial, forever, final},
    discounts[{type, value, duration, ...}],
    obligation, obligationLabel.

L'extraction est donc 100 % dynamique : aucun mapping codé en dur, contrairement
au scraper SFR. Le débit, le Wi-Fi et la durée de promo viennent du store
lui-même, pas d'un catalogue local.

Périmètre Phase 2A
------------------
Trois Bbox principales : `Bbox fit`, `Bbox must`, `Bbox ultym`. Les variantes
"Banque", "Gaming", "Smart TV" et les box 4G/5G sont exclues (hors scope du
comparateur fibre core). Le store contient des doublons (même offre référencée
sous plusieurs onglets) : on dédoublonne par `name`, en préférant la variante
"sans engagement" si elle existe (sinon la version courte d'engagement).

Limitations connues — Phase 2C
------------------------------
- `setup_fee` est fixé à 48 € (tarif officiel des Bbox FTTH) même si la
  promo en cours offre les frais de mise en service. Le schéma actuel ne
  distingue pas tarif officiel vs offre commerciale (champ `setup_fee_waived`
  à introduire en Phase 2C, cf. JOURNAL).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from scraper.operators.base import BaseScraper

logger = logging.getLogger(__name__)


# Tarif officiel Bbox FTTH ; la promo "frais offerts" n'est pas captée.
# Voir JOURNAL Tâche 2A.6 pour la dette technique correspondante.
SETUP_FEE_FTTH_BBOX = 48.0

# Offres "core" du catalogue fibre — exclut variantes Banque / Gaming /
# Smart TV / 4G / 5G qui sont des bundles spécialisés.
CORE_OFFER_NAMES: set[str] = {"Bbox fit", "Bbox must", "Bbox ultym"}


def _parse_rate_to_mbps(s: str) -> int | None:
    """Convertit '8 Gb/s', '700 Mb/s', '1Gbs', '1 Gbit/s' → Mbps."""
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*(G|M)b(?:it)?\s*/?\s*s?\b", s, re.I)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    unit = m.group(2).upper()
    return int(round(value * 1000)) if unit == "G" else int(round(value))


def _find_store_script(html: str) -> str:
    """Localise le script Next.js qui contient le store des offres FAI.
    Critère : présence simultanée de `downRates` et `rangeNg`."""
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    candidates = [s for s in scripts if "downRates" in s and "rangeNg" in s]
    if not candidates:
        raise ValueError(
            "Store Bouygues introuvable : aucun <script> ne contient "
            "à la fois 'downRates' et 'rangeNg'. La page a peut-être changé."
        )
    return max(candidates, key=len)


def _extract_categories(window: str) -> list[str]:
    m = re.search(r'\\"categories\\":\[([^\]]*?)\]', window)
    if not m:
        return []
    return re.findall(r'\\"([^\\"]+)\\"', m.group(1))


def _extract_price(window: str) -> dict[str, float] | None:
    """Extrait `details.price.{initial, forever, final}`."""
    m = re.search(
        r'\\"details\\":\{\\"price\\":\{\\"initial\\":(\d+(?:\.\d+)?),'
        r'\\"subsidized\\":(?:"\$undefined"|\\"\$undefined\\"|\d+(?:\.\d+)?),'
        r'\\"forever\\":(\d+(?:\.\d+)?),'
        r'\\"final\\":(\d+(?:\.\d+)?)\}',
        window,
    )
    if not m:
        return None
    return {
        "initial": float(m.group(1)),
        "forever": float(m.group(2)),
        "final": float(m.group(3)),
    }


def _extract_promo_duration_months(window: str) -> int | None:
    """Extrait la durée de la 1re promo (`discounts[].duration` en mois)."""
    m = re.search(r'\\"discounts\\":\[\{[^}]*?\\"duration\\":(\d+)', window)
    return int(m.group(1)) if m else None


def _extract_obligation(window: str) -> str | None:
    m = re.search(r'\\"obligation\\":\\"(\w+)\\"', window)
    return m.group(1) if m else None


def _obligation_to_months(obligation: str | None) -> int:
    if obligation is None or obligation == "none":
        return 0
    m = re.match(r"monthly(\d+)", obligation)
    if m:
        return int(m.group(1))
    logger.warning("[bouygues] obligation inconnue : %r — défaut 0", obligation)
    return 0


def _extract_wifi_standard(window: str) -> str | None:
    """Détecte le standard WiFi dans la fenêtre du produit.

    Sources successives : icon `tri-wifi-N` / `wifi-N`, ou label
    `WiFi N tri/bi-bande`.
    """
    m = re.search(r'\\"(?:tri-)?wifi-(\d+)\\"', window)
    if m:
        return f"Wi-Fi {m.group(1)}"
    m = re.search(r'\\"label\\":\\"Wi-?Fi\s*(\d+)', window)
    if m:
        return f"Wi-Fi {m.group(1)}"
    return None


def _display_name(raw_name: str) -> str:
    """'Bbox fit' → 'Bbox Fit'. Capitalise tous les mots après 'Bbox'."""
    parts = raw_name.split()
    if not parts:
        return raw_name
    return parts[0] + " " + " ".join(p.capitalize() for p in parts[1:])


class BouyguesScraper(BaseScraper):
    OPERATOR_SLUG = "bouygues"
    BASE_URL = "https://www.bouyguestelecom.fr/offres-internet"

    def parse_offers(self, html: str) -> list[dict[str, Any]]:
        store = _find_store_script(html)
        by_name: dict[str, dict[str, Any]] = {}

        for m in re.finditer(r'\\"name\\":\\"(Bbox [^\\"]+)\\"', store):
            raw_name = m.group(1).strip()
            if raw_name not in CORE_OFFER_NAMES:
                continue

            # Fenêtre du produit (5000 chars, suffisant pour englober tous
            # les champs : price, discounts, obligation, downRates, etc.).
            window = store[m.start():m.start() + 5000]

            # Filtre techno + catégorie (FTTH + 'fai').
            tech_match = re.search(r'\\"technology\\":\\"(\w+)\\"', window)
            if not tech_match or tech_match.group(1) != "FTTH":
                continue
            categories = _extract_categories(window)
            if "fai" not in categories:
                continue

            # Débits.
            down_match = re.search(r'\\"downRates\\":\\"([^\\"]+)\\"', window)
            up_match = re.search(r'\\"upRates\\":\\"([^\\"]+)\\"', window)
            if not down_match or not up_match:
                logger.warning("[bouygues] %r : downRates/upRates manquants — skip", raw_name)
                continue
            download_mbps = _parse_rate_to_mbps(down_match.group(1))
            upload_mbps = _parse_rate_to_mbps(up_match.group(1))
            if download_mbps is None or upload_mbps is None:
                logger.warning(
                    "[bouygues] %r : débit illisible (↓=%r ↑=%r) — skip",
                    raw_name, down_match.group(1), up_match.group(1),
                )
                continue

            # Prix.
            price = _extract_price(window)
            if price is None:
                logger.warning("[bouygues] %r : price introuvable — skip", raw_name)
                continue

            # Engagement + promo.
            commitment_months = _obligation_to_months(_extract_obligation(window))
            promo_duration = _extract_promo_duration_months(window)
            promo_price = price["final"] if price["final"] != price["forever"] else None

            # Wi-Fi.
            wifi_standard = _extract_wifi_standard(window)

            offer = {
                "operator_slug": self.OPERATOR_SLUG,
                "type": "fibre",
                "name": _display_name(raw_name),
                "monthly_price": price["forever"],
                "promo_price": promo_price,
                "promo_duration_months": promo_duration if promo_price is not None else None,
                "commitment_months": commitment_months,
                "setup_fee": SETUP_FEE_FTTH_BBOX,
                "source_url": self.BASE_URL,
                "score": None,
                "fibre_specs": {
                    "download_mbps": download_mbps,
                    "upload_mbps": upload_mbps,
                    "technology": "FTTH",
                    "wifi_standard": wifi_standard,
                    "has_tv": False,
                    "tv_channels_count": None,
                    "has_landline": True,
                },
            }

            # Dédup par nom : préférer "sans engagement" puis durée la plus courte.
            display_name = offer["name"]
            existing = by_name.get(display_name)
            if existing is not None:
                if existing["commitment_months"] == 0:
                    continue
                if commitment_months >= existing["commitment_months"]:
                    continue
            by_name[display_name] = offer

        if not by_name:
            logger.warning("[bouygues] aucune offre extraite — la page a peut-être changé")
        return list(by_name.values())
