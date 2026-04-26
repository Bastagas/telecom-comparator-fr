"""Scraper Free — Phase 1 walking skeleton, cible unique : Freebox Pop.

Robustesse minimale : on extrait par signatures regex sur du texte
significatif (« Gbit/s en descendant », « Frais de mise en service NN€ »,
etc.) plutôt que par sélecteurs CSS Tailwind qui changent souvent.
La qualité du parsing sera renforcée en Phase 2.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from scraper.db import upsert_offer

logger = logging.getLogger(__name__)

URL_FREEBOX_POP = "https://www.free.fr/freebox/freebox-pop/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _gbits_to_mbps(value: float) -> int:
    return int(round(value * 1000))


def parse_freebox_pop(html: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extrait l'offre Freebox Pop et ses fibre_specs depuis le HTML.

    Lève ValueError si une donnée critique manque — on préfère échouer
    fort plutôt qu'insérer du bruit en BDD.
    """
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
    commitment_months = 0 if "Sans engagement" in html else None
    if commitment_months is None:
        raise ValueError("Engagement non identifié")

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
        "type": "fibre",
        "name": "Freebox Pop",
        "monthly_price": monthly_price,
        "promo_price": promo_price,
        "promo_duration_months": 12,
        "commitment_months": commitment_months,
        "setup_fee": setup_fee,
        "source_url": URL_FREEBOX_POP,
        "score": None,
    }

    fibre_specs = {
        "download_mbps": download_mbps,
        "upload_mbps": upload_mbps,
        "technology": "FTTH",
        "wifi_standard": wifi_standard,
        "has_tv": True,
        "tv_channels_count": None,
        "has_landline": True,
    }

    return offer, fibre_specs


def fetch_html(url: str = URL_FREEBOX_POP) -> str:
    logger.info("GET %s", url)
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


def scrape() -> int:
    html = fetch_html()
    offer, fibre_specs = parse_freebox_pop(html)
    logger.info(
        "Parsed Freebox Pop: %.2f€/mois (promo %.2f€), %d/%d Mbps, %s",
        offer["monthly_price"],
        offer["promo_price"],
        fibre_specs["download_mbps"],
        fibre_specs["upload_mbps"],
        fibre_specs["wifi_standard"],
    )
    return upsert_offer("free", offer, fibre_specs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    offer_id = scrape()
    print(f"Offer id={offer_id}")
