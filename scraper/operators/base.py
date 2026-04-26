"""Classe abstraite BaseScraper — ossature commune aux scrapers d'opérateurs.

Le squelette (fetch HTTP par défaut, orchestration, upsert, gestion d'erreurs)
est mutualisé. Chaque sous-classe définit sa propre stratégie d'extraction
(`parse_offers`) — regex sur HTML brut, JSON-LD, microdata, etc. —
sans contrainte imposée par la classe parente.

Contrat de retour de `parse_offers(html)` : list[dict] où chaque dict contient
au minimum les clés suivantes (`fibre_specs` est imbriqué) :

    {
        "operator_slug":         str,                # slug de la table operators
        "type":                  "fibre"|"mobile"|"bundle",
        "name":                  str,
        "monthly_price":         float,              # prix de base (post-promo)
        "promo_price":           float | None,
        "promo_duration_months": int | None,
        "commitment_months":     int,                # 0 = sans engagement
        "setup_fee":             float,
        "source_url":            str,
        "score":                 float | None,       # NULL Phase 1, calculé en 2A.2
        "fibre_specs": {                             # None si type != fibre
            "download_mbps":     int,
            "upload_mbps":       int,
            "technology":        "FTTH"|"FTTLA"|"VDSL"|"ADSL",
            "wifi_standard":     str | None,
            "has_tv":            bool,
            "tv_channels_count": int | None,
            "has_landline":      bool,
        } | None,
    }

Ce dict est le format consommé par `scraper.db.upsert_offer`.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import requests

from scraper.db import upsert_offer

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    OPERATOR_SLUG: str = ""
    BASE_URL: str = ""

    REQUEST_HEADERS: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    REQUEST_TIMEOUT: int = 25  # secondes

    def __init__(self) -> None:
        if not self.OPERATOR_SLUG or not self.BASE_URL:
            raise ValueError(
                f"{type(self).__name__} doit définir OPERATOR_SLUG et BASE_URL"
            )

    def fetch_html(self) -> str:
        """Implémentation par défaut : requests + headers de classe.

        Une sous-classe peut surcharger pour Playwright si un site bascule
        en JS-only (cf. PHASE_2_PLAN — non requis Phase 2A d'après le scout).
        """
        logger.info("[%s] GET %s", self.OPERATOR_SLUG, self.BASE_URL)
        response = requests.get(
            self.BASE_URL,
            headers=self.REQUEST_HEADERS,
            timeout=self.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text

    @abstractmethod
    def parse_offers(self, html: str) -> list[dict[str, Any]]:
        """Extrait la liste des offres depuis le HTML.

        Implémentation libre par sous-classe (regex, JSON-LD, microdata, etc.).
        Doit respecter le contrat de dict documenté dans le module.
        """
        ...

    def run(self) -> int:
        """Orchestre fetch + parse + upsert.

        Retourne le nombre d'offres effectivement upsertées. Toute exception
        levée par fetch_html / parse_offers / upsert_offer est rattrapée et
        loggée — un opérateur qui échoue ne casse pas le pipeline global.
        """
        try:
            html = self.fetch_html()
            offers = self.parse_offers(html)
        except Exception as exc:
            logger.exception("[%s] échec fetch/parse : %s", self.OPERATOR_SLUG, exc)
            return 0

        upserted = 0
        for offer in offers:
            try:
                upsert_offer(offer)
                upserted += 1
            except Exception as exc:
                logger.exception(
                    "[%s] échec upsert offre %r : %s",
                    self.OPERATOR_SLUG, offer.get("name", "?"), exc,
                )

        logger.info(
            "[%s] scraped %d offer%s",
            self.OPERATOR_SLUG, upserted, "s" if upserted > 1 else "",
        )
        return upserted
