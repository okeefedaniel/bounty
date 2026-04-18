# Bounty

**Federal Grants Intelligence for state and local governments.**

Discovery, tracking, and AI-powered matching across federal grant opportunities. Part of the [DockLabs](https://docklabs.ai) suite.

## What it does

- **Opportunity feed** — Syncs federal grant postings from Grants.gov and surfaces them in a filterable portal.
- **Preference-based matching** — Users define keyword, agency, and state preferences; Bounty scores incoming opportunities for relevance.
- **AI relevance scoring** — Claude-powered match scoring with natural-language explanations (BYO Anthropic API key per user).
- **Tracking + handoff** — Flag opportunities for follow-up and hand them off to [Harbor](https://harbor.docklabs.ai) for full application lifecycle management.

## Part of the DockLabs suite

Bounty shares common infrastructure with the rest of the DockLabs suite (Harbor, Beacon, Helm, Lookout, and others) via the [Keel](https://github.com/okeefedaniel/keel) shared platform: auth/RBAC, audit logging, notifications, SSO, and UI patterns.

## Tech Stack

Django 5.2 · PostgreSQL 16 (SQLite for dev) · Bootstrap 5.3 · Django REST Framework · django-allauth (SSO + MFA) · Anthropic Claude API · Railway (dev) · AWS GovCloud (production)

## Quick Start

```bash
git clone https://github.com/okeefedaniel/bounty.git
cd bounty
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in secrets
python manage.py migrate
python manage.py runserver
```

## License

MIT
