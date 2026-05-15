# AGENTS.md

This file provides guidance to Codex when working with this project.

## Project Overview

**server-console** is a Flask backend for a management console. It currently covers:

- Cookie-based JWT login and user management.
- Wedding photo wall and wedding music management.
- Weight management APIs served from this backend.
- Alibaba Cloud OSS upload credential generation and image metadata sync.
- Restaurant dish management under a separate `/api/chuan-dai` API namespace and database.

For a fuller read of the current architecture and risks, see `docs/PROJECT_ANALYSIS.md`.

## Tech Stack

- **Framework**: Flask
- **ORM**: Flask-SQLAlchemy / SQLAlchemy
- **Database**: PostgreSQL, usually Supabase
- **Auth**: Flask-JWT-Extended with JWT stored in cookies
- **Storage**: Alibaba Cloud OSS, Chengdu region
- **Async**: Celery + Redis
- **Deployment**: Docker + Gunicorn + Kubernetes

## Key Commands

```bash
# Run locally
python app.py

# Run tests if a tests/ directory is added
python -m pytest tests/

# Build the container
docker build -t server-console .
```

There is currently no real `tests/` directory. `api/test_api.py` contains Flask diagnostic endpoints, not pytest tests.

## Important Files

- `app.py` - Flask entry point, extension setup, JWT refresh hook, table initialization, blueprint registration, Celery setup, health check.
- `config.py` - Database, JWT, Redis, and OSS configuration from environment variables.
- `extensions.py` - Shared `db` and `jwt` extension instances.
- `mycelery.py` - Celery factory and task registration.
- `api/` - Flask blueprint route handlers. Every `*_api.py` module is auto-registered.
- `model/` - SQLAlchemy models.
- `utils/register_api_blueprints.py` - Auto-registers blueprints and applies URL prefixes.
- `utils/db_utils.py` - Imports models and attempts to create missing tables at startup.
- `utils/db_router.py` - Utility for choosing a DB by URL path; currently not part of the main request path.
- `supabase/migrations/001_initial_tables.sql` - Initial Supabase schema script.
- `Dockerfile`, `gunicorn_config.py`, `deployment.yaml` - Container and Kubernetes deployment.

## Routing Conventions

`utils/register_api_blueprints.py` scans `api/*_api.py` and expects each module to expose a blueprint named `<module_name>_pb`.

- `dish_api.py` is registered with `/api/chuan-dai`.
- All other APIs are registered with `/api`.

Examples:

- `auth_api.py` route `/auth/login` becomes `/api/auth/login`.
- `wedding_api.py` route `/wedding/photo/wall/list` becomes `/api/wedding/photo/wall/list`.
- `dish_api.py` route `/dish/list` becomes `/api/chuan-dai/dish/list`.

## Databases

`config.py` defines:

- `DATABASE_URL`: default management-console DB.
- `DATABASE_URL_RESTAURANT`: restaurant DB for dish APIs.

Default Flask-SQLAlchemy models use `DATABASE_URL`. `api/dish_api.py` creates its own SQLAlchemy engine/session against `DATABASE_URL_RESTAURANT`.

Be careful when changing startup behavior: `create_missing_tables(app)` imports all models and calls `db.create_all()` if it thinks any model table is missing.

## Data Models

- `User` -> `app_user`
- `WeddingPhotoWall` -> `wedding_photo_wall`
- `WeddingMusic` -> `wedding_music`
- `Image` -> `image`
- `Dish` -> `Dish` in the restaurant database
- `WeightRecord` -> `weight_record`

## Weight APIs

Weight management routes are defined in `api/weight_api.py`, registered under `/api`:

- `POST /api/weight/record/add`
- `POST /api/weight/record/edit`
- `POST /api/weight/record/delete`
- `GET /api/weight/records`
- `GET /api/weight/records/all`
- `GET /api/weight/record/latest`
- `GET /api/weight/summary`

These routes require JWT and use the JWT identity as `user_identity`, so each login user only reads and mutates their own records.

## Auth Notes

- JWT token location is cookies.
- `app.py` refreshes access tokens in `after_request` when expiry is within 5 minutes.
- JWT errors return JSON payloads with business codes like `5001`, `5002`, etc.
- Many business errors return HTTP 200 with a non-200 business `code`; preserve this behavior unless the frontend is updated too.

## Known Risks To Check Before Editing

- `auth_api.py` uses `bcrypt.checkpw`, while `user_api.py` creates passwords with Werkzeug `pbkdf2:sha256`. Newly created users may not be able to log in.
- `upload_api.py` calls `Image(name=filename, path=filesave)`, but `Image.__init__` requires `last_modified`, `size`, and `content_type`.
- `supabase/migrations/001_initial_tables.sql` uses `order_num` for photo wall ordering, while the SQLAlchemy model uses `order`.
- Some write/admin endpoints lack `@jwt_required()`, especially wedding and dish management endpoints.
- `DATABASE_URL_RESTAURANT` defaults to an empty string, but `dish_api.py` creates an engine at import time.
- There is no pytest suite yet.

## Code Style

- Follow Python PEP 8.
- Keep Flask routes grouped by blueprint in `api/`.
- Keep SQLAlchemy models in `model/`.
- Prefer small, explicit fixes that preserve existing API response shapes.
- Use environment variables for secrets and deployment-specific settings.
