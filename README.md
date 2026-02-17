# Discord Messages Reporting API

Pipeline complet pour :

1. Collecter les messages d'un ou plusieurs salons Discord ciblés.
2. Les stocker en base SQL.
3. Les exposer via une API REST JSON exploitable pour du reporting.

> Le projet est volontairement découplé de PowerBI pour rester agnostique côté BI.

## Architecture

- **Ingestion temps réel** : `app/discord/ingestor.py`
- **Backfill historique** : `scripts/backfill.py`
- **API REST** : `app/main.py` + `app/api/routes.py`
- **Stockage** : SQLAlchemy (SQLite par défaut, PostgreSQL possible via `DATABASE_URL`)

## Prérequis

- Python 3.11+
- Un bot Discord créé dans Discord Developer Portal
- Intents activés:
  - Guilds
  - Guild Messages
  - Message Content

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Compléter `.env`:

```env
API_KEY=super-secret-key
DATABASE_URL=sqlite:///./discord_messages.db
DISCORD_BOT_TOKEN=xxx
DISCORD_GUILD_ID=123456789012345678
DISCORD_CHANNEL_IDS=123456789012345678,987654321098765432
```

## Lancement

### 1) API

```bash
./scripts/run_api.sh
```

- Healthcheck: `GET /health`
- Swagger: `GET /docs`

### 2) Ingestion temps réel

```bash
./scripts/run_ingestor.sh
```

### 3) Backfill historique (optionnel au démarrage)

```bash
python scripts/backfill.py
```

## Endpoints API

Tous les endpoints `/v1/*` demandent le header:

```http
x-api-key: <API_KEY>
```

### `GET /v1/messages`

Query params:

- `guild_id` (int, requis)
- `channel_id` (int, requis)
- `from` (ISO-8601, optionnel)
- `to` (ISO-8601, optionnel)
- `cursor` (message_id, optionnel)
- `limit` (1..500, défaut 100)
- `include_deleted` (bool, défaut false)

Exemple:

```bash
curl -H "x-api-key: super-secret-key" \
  "http://localhost:8000/v1/messages?guild_id=123&channel_id=456&from=2025-01-01T00:00:00Z&limit=200"
```

### `GET /v1/messages/{message_id}`

Retourne le détail d'un message s'il est présent en base.

## Modèle de données principal

Table `discord_messages`:

- `message_id` (PK)
- `guild_id`, `channel_id`, `author_id`
- `author_name`
- `content`
- `created_at`, `edited_at`
- `deleted`
- `attachment_count`, `embed_count`
- `raw_json` (payload brut)
- `ingested_at`

## Sécurité et bonnes pratiques

- Ne jamais commiter `.env`.
- Régénérer le token bot en cas de fuite.
- Utiliser un reverse proxy HTTPS en production.
- Ajouter rate limiting côté API si exposition hors réseau privé.

## Démo rapide

1. Lancer API + ingestor
2. Envoyer un message sur le salon Discord ciblé
3. Interroger:

```bash
curl -H "x-api-key: super-secret-key" \
  "http://localhost:8000/v1/messages?guild_id=<GUILD_ID>&channel_id=<CHANNEL_ID>"
```

Tu obtiens un JSON exploitable directement par une couche de reporting.
