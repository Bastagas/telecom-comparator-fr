"""Connexion MySQL pour l'API.

Volontairement indépendant de scraper.db — l'API ne doit pas importer
le module scraper. Découplage des couches : scraper et API peuvent être
déployés séparément avec leurs deps minimales.
"""

from __future__ import annotations

import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )
