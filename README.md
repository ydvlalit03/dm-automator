# DM Automator

Turn comments into conversations. **DM Automator** watches your Instagram & LinkedIn posts for comments, matches them against campaign keywords, and automatically sends personalized direct messages — so leads get an instant, relevant reply while intent is high. Built for "comment X to get Y" campaigns.

---

## How It Works

```
IG / LinkedIn comment → Webhook / Poller → Keyword Matcher → DM Queue → DM Sender (async loop) → DM sent + logged
```

---

## Features

- **Comment → DM automation** — triggers a DM when a comment matches a campaign
- **Keyword matching** — per-campaign rules decide who gets messaged and what they receive
- **Campaigns & materials** — multiple campaigns, each with its own keywords and delivery material (links, offers, lead magnets)
- **Admin dashboard** — server-rendered UI to manage campaigns and view stats
- **Background workers** — async DM-sender queue and a LinkedIn poller
- **Webhooks + polling** — Instagram via webhooks, LinkedIn via polling
- **Secure auth** — bcrypt-hashed passwords + session middleware
- **Full audit trail** — comment logs, DM logs and a DM queue persisted in the DB

---

## Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database**: SQLAlchemy ORM + pydantic-settings
- **Auth**: passlib + bcrypt, Starlette session middleware
- **Frontend**: server-rendered Jinja2 + vanilla JS/CSS
- **HTTP**: httpx (Instagram / LinkedIn APIs)
- **Deploy**: Docker + docker-compose (see `DEPLOY.md`)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Instagram Graph API / LinkedIn API credentials

### Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY and your IG/LinkedIn API keys

uvicorn main:app --reload       # http://localhost:8000
```

Run with Docker: `docker-compose up --build`. A free-tier deploy guide (Oracle Cloud + Cloudflare Tunnel) is in [`DEPLOY.md`](./DEPLOY.md).

---

## Project Structure

```
routers/   # webhooks, campaigns, posts, dashboard, auth, linkedin_admin
services/   # instagram, linkedin, keyword_matcher, dispatcher, url_resolver
tasks/      # dm_sender + linkedin_poller background loops
models/     # Campaign, Material, InstagramPost, DMQueue, CommentLog, DMLog, User
```

---

## Disclaimer

Use responsibly and in compliance with Instagram Platform Policy, LinkedIn API Terms, and applicable anti-spam / data-privacy regulations.
