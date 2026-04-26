# Comparateur d'offres télécom FR

Projet de master couplant scraping Python, BDD MySQL, frontend PHP et API Flask, enrichi des données régulateur ARCEP.

## Statut

🚧 Phase 1 — Walking skeleton (en cours)

## Quick start

### Pré-requis

- MAMP démarré (MySQL sur `127.0.0.1:8889`, user `root` / pass `root`).
- Python 3.12+.
- Base `telecom_comparator` créée via `00_brief/data_model.sql`.

### Scraper Python

```bash
# 1. Venv (à la racine du projet)
python3 -m venv .venv
source .venv/bin/activate

# 2. Dépendances
pip install -r scraper/requirements.txt

# 3. Config
cp scraper/.env.example .env   # puis ajuster si besoin

# 4. Lancer le pipeline (Phase 1 : Free uniquement)
python -m scraper.pipeline
```

Logs sur stdout. L'upsert est idempotent (UNIQUE KEY sur `offers(operator_id, type, name)`).

## Documentation

Voir `00_brief/PROJECT_BRIEF.md` pour la vue d'ensemble du projet, le phasage et les conventions.
