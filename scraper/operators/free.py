"""Scraper Free — Phase 1 walking skeleton, cible unique : Freebox Pop.

Refactor Phase 2A.1 : devient une instance de BaseScraper. La logique
d'extraction (regex sur HTML brut Tailwind) est inchangée — on choisit
volontairement de ne pas la réécrire à cette étape.

Robustesse minimale : extraction par signatures regex sur du texte
significatif (« Gbit/s en descendant », « Frais de mise en service NN€ »,
etc.) plutôt que par sélecteurs CSS Tailwind qui changent souvent.
"""

from __future__ import annotations

import re
from typing import Any

from scraper.operators.base import BaseScraper


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _gbits_to_mbps(value: float) -> int:
    return int(round(value * 1000))


class FreeScraper(BaseScraper):
    OPERATOR_SLUG = "free"
    BASE_URL = "https://www.free.fr/freebox/freebox-pop/"

    def parse_offers(self, html: str) -> list[dict[str, Any]]:
        # Prix promo + prix après promo : "29,99€/mois" ... "pendant 1 an puis 39,99€/mois"
        promo_match = re.search(
            r"(\d{1,3}[,.]\d{2})\s*€/mois\s*</p>.{0,200}?pendant\s+1\s+an\s+puis\s+(\d{1,3}[,.]\d{2})\s*€/mois",
            html,
            re.S,
        )
        if not promo_match:
            raise ValueError("Prix mensuel et promo non trouvés sur la page Freebox Pop")
        promo_price = _to_float(promo_match.group(1))
        monthly_price = _to_float(promo_match.group(2))

        # Engagement
        if "Sans engagement" not in html:
            raise ValueError("Engagement non identifié")
        commitment_months = 0

        # Frais de mise en service : "Frais de mise en service 49€"
        setup_match = re.search(r"Frais de mise en service\s*(\d{1,3})\s*€", html)
        if not setup_match:
            raise ValueError("Frais de mise en service non trouvés")
        setup_fee = float(setup_match.group(1))

        # Débit descendant : "jusqu'à 5 Gbit/s partagés en descendant"
        down_match = re.search(
            r"jusqu['’]à\s*(\d{1,3}(?:[,.]\d+)?)\s*Gbit/?s\s*(?:partagés\s*)?en\s*descendant",
            html,
            re.I,
        )
        if not down_match:
            raise ValueError("Débit descendant non trouvé")
        download_mbps = _gbits_to_mbps(_to_float(down_match.group(1)))

        # Débit montant : un chiffre suivi de "Mbit/s" puis "en débit montant"
        up_match = re.search(
            r"(\d{2,5})\s*</p>\s*<p[^>]*>\s*Mbit/?s\s*</p>.{0,200}?en\s*débit\s*montant",
            html,
            re.I | re.S,
        )
        if not up_match:
            raise ValueError("Débit montant non trouvé")
        upload_mbps = int(up_match.group(1))

        # WiFi
        wifi_match = re.search(r"Wi-?Fi\s*(7|6E|6|5)", html)
        wifi_standard = f"Wi-Fi {wifi_match.group(1)}" if wifi_match else None

        offer = {
            "operator_slug": self.OPERATOR_SLUG,
            "type": "fibre",
            "name": "Freebox Pop",
            "monthly_price": monthly_price,
            "promo_price": promo_price,
            "promo_duration_months": 12,
            "commitment_months": commitment_months,
            "setup_fee": setup_fee,
            "source_url": self.BASE_URL,
            "score": None,
            "fibre_specs": {
                "download_mbps": download_mbps,
                "upload_mbps": upload_mbps,
                "technology": "FTTH",
                "wifi_standard": wifi_standard,
                "has_tv": True,
                "tv_channels_count": None,
                "has_landline": True,
            },
        }
        return [offer]
