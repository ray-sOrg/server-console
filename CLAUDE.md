# CLAUDE.md

This file provides guidance to Claude Code when working with this project.

See https://docs.claude.com/ claude-code/projects for more information.

## Project Overview

**server-console** - Wedding service management backend system with photo wall and music management features.

## Tech Stack

- **Framework**: Flask + SQLAlchemy
- **Database**: PostgreSQL (Supabase)
- **Auth**: JWT with cookie storage
- **Storage**: Alibaba Cloud OSS
- **Async**: Celery + Redis
- **Deployment**: Docker + Kubernetes

## Key Commands

```bash
# Run locally
python app.py

# Run tests
python -m pytest tests/

# Database migrations (if any)
flask db upgrade
```

## Code Style

- Python PEP 8 style
- Use type hints where helpful
- Flask blueprints for API organization
- SQLAlchemy models in `model/` directory

## Important Files

- `app.py` - Application entry point
- `config.py` - Configuration settings
- `api/` - API route handlers
- `model/` - Database models

## Development Notes

- JWT tokens stored in cookies
- OSS uses Alibaba Cloud Chengdu region
- Async tasks via Celery for image sync
- Supabase for PostgreSQL database
