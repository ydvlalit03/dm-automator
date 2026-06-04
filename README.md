<div align="center">

# 📨 DM Automator

### Turn comments into conversations — auto-send personalized DMs on Instagram & LinkedIn

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white)
![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)

</div>

---

## 📖 Overview

Creators run "**comment _X_ to get _Y_**" campaigns all the time — but replying to every commenter by hand doesn't scale, and the longer you wait, the colder the lead. **DM Automator** closes that gap: it watches your Instagram and LinkedIn posts for comments, matches them against your campaign keywords, and **automatically sends a personalized direct message** the moment intent is highest.

Set up a campaign with a keyword and the material to deliver (a link, lead magnet, or offer), and the automator handles detection, matching, queuing, sending, and logging — all from a self-hosted admin dashboard.

---

## 📑 Table of Contents

- [How it works](#-how-it-works)
- [Features](#-features)
- [Tech stack](#-tech-stack)
- [Data model](#-data-model)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Project structure](#-project-structure)
- [Disclaimer](#-disclaimer)

---

## 🔄 How it works

```
IG / LinkedIn comment
        │
        ▼
 Webhook / Poller ──▶ Keyword Matcher ──▶ DM Queue ──▶ DM Sender (async loop) ──▶ DM sent
        │                  │                                                          │
        ▼                  ▼                                                          ▼
   CommentLog        Campaign rules                                              DMLog (audit)
```

Instagram events arrive via **webhooks**; LinkedIn activity is picked up by a **background poller**. Matches are written to a **DM queue**, and a separate async **DM-sender** loop drains the queue and dispatches messages — so spikes in comments never block sending.

---

## ✨ Features

- **💬 Comment → DM automation** — fires a DM when a comment matches a campaign
- **🔑 Keyword matching** — per-campaign rules decide who gets messaged and what they receive
- **📣 Campaigns & materials** — run multiple campaigns, each with its own keywords and delivery material (links, offers, lead magnets)
- **📊 Admin dashboard** — server-rendered UI to manage campaigns, posts and view stats
- **🔁 Background workers** — async DM-sender queue + a LinkedIn poller run as independent loops
- **🪝 Webhooks + polling** — Instagram via webhooks, LinkedIn via polling
- **🔐 Secure auth** — admin login with bcrypt-hashed passwords + session middleware; the seed admin is created on first run
- **📝 Full audit trail** — comment logs, DM logs and a DM queue persisted to the database

---

## 🛠️ Tech stack

| Concern | Technology |
|---------|------------|
| **Framework** | FastAPI + Uvicorn |
| **Database** | SQLAlchemy ORM + pydantic-settings config |
| **Auth** | passlib + bcrypt, Starlette `SessionMiddleware` |
| **Frontend** | server-rendered Jinja2 templates + vanilla JS/CSS |
| **HTTP** | httpx (Instagram / LinkedIn API calls) |
| **Deployment** | Docker + docker-compose |

---

## 🗄️ Data model

| Model | Purpose |
|-------|---------|
| `User` | admin accounts (bcrypt-hashed) |
| `Campaign` | a keyword campaign with its delivery material |
| `Material` | the asset delivered in the DM (link / offer / lead magnet) |
| `InstagramPost` | tracked posts |
| `DMQueue` | pending DMs awaiting send |
| `CommentLog` | every comment seen |
| `DMLog` | every DM dispatched (audit trail) |

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- Instagram Graph API / LinkedIn API credentials

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY and your IG/LinkedIn API keys

uvicorn main:app --reload        # http://localhost:8000
```

The admin user is seeded automatically from `ADMIN_EMAIL` / `ADMIN_PASSWORD` on first startup.

---

## ⚙️ Configuration

| Variable | Purpose |
|----------|---------|
| `ADMIN_EMAIL` | seed admin account email |
| `ADMIN_PASSWORD` | seed admin account password |
| `SECRET_KEY` | session signing key (32+ chars; auto-generated if left as the placeholder) |
| Instagram / LinkedIn keys | platform API access |

---

## 🚀 Deployment

Run locally with Docker:

```bash
docker-compose up --build
```

A complete **free-tier deployment guide** (Oracle Cloud ARM instance + Cloudflare Tunnel, ~30 min, \$0/month) is documented in [`DEPLOY.md`](./DEPLOY.md).

---

## 🗂️ Project structure

```
routers/   # webhooks, campaigns, posts, dashboard, auth, linkedin_admin
services/   # instagram, linkedin, keyword_matcher, dispatcher, url_resolver
tasks/      # dm_sender + linkedin_poller background loops
models/     # User, Campaign, Material, InstagramPost, DMQueue, CommentLog, DMLog
schemas/    # campaign, stats Pydantic schemas
static/     # dashboard JS/CSS
main.py · config.py · auth.py · database.py · Dockerfile · docker-compose.yml
```

---

## ⚠️ Disclaimer

Use responsibly and in compliance with the **Instagram Platform Policy**, **LinkedIn API Terms**, and applicable anti-spam / data-privacy regulations. Automated messaging must respect platform rules and user consent.
