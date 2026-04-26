# Comparateur d'offres télécom FR

> Outil de veille qui agrège les offres commerciales des 4 opérateurs télécom français (Orange, SFR, Bouygues, Free) et les enrichit avec les données du régulateur ARCEP.

**Pourquoi ce projet ?** Démontrer un pipeline data complet de bout en bout : scraping Python → BDD relationnelle MySQL → frontend PHP → API REST Flask. Le projet sert également de POC d'outil de veille télécom dans un contexte de conseil sectoriel.

**Statut** : 🚧 Phase 1 (walking skeleton) — pipeline complet sur 1 opérateur (Free Freebox Pop). Phase 2 à suivre : 4 opérateurs + enrichissement ARCEP par commune.

**Stack** : Python 3.12 (scraping + Flask), MySQL 8 (MAMP en dev), PHP 8, Flask 3.

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

### API Flask

```bash
# Deps API (dans le même venv)
pip install -r api/requirements.txt

# Lancer l'API
python -m api.app
# → Running on http://127.0.0.1:5001
```

**Port** : 5001 par défaut. Sur macOS Monterey+, le port 5000 est réservé par
l'AirPlay Receiver (process `ControlCenter`), d'où ce choix. Le port est
configurable via la variable `API_PORT` du `.env`.

**Endpoints Phase 1**

- `GET /api/offers` — liste des offres actives.
- `GET /api/offers/<id>` — détail d'une offre (specs, options, opérateur). 404 si id inconnu.

Filtres avancés, pagination, `/api/operators`, endpoints couverture ARCEP : Phase 2.

**Exemples curl**

```bash
curl -s http://localhost:5001/api/offers | python3 -m json.tool
curl -s http://localhost:5001/api/offers/1 | python3 -m json.tool
curl -i -s http://localhost:5001/api/offers/9999    # → 404 JSON
```

### Front PHP via MAMP

L'écran 2 (`results.php`) implémente le design Direction C (cf. `00_brief/dc/`).

**Setup MAMP** — un symlink dans `htdocs` évite de déplacer le projet ou de
toucher la config Apache partagée :

```bash
ln -s ~/dev/telecom-comparator-fr/web /Applications/MAMP/htdocs/telecom
```

Puis dans le navigateur :

```
http://localhost:8888/telecom/results.php
```

`index.php` redirige vers `results.php` (Phase 1 : pas encore d'écran d'accueil).

**Filtres GET** (Phase 1, infrastructure prête, peu d'effet avec une seule offre) :
`?operator=free&type=fibre&max_price=60`.

## Documentation

Voir `00_brief/PROJECT_BRIEF.md` pour la vue d'ensemble du projet, le phasage et les conventions.
