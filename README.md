# 📨 DM Automator

> Turn comments into conversations. **DM Automator** watches your Instagram & LinkedIn posts for comments, matches them against campaign keywords, and automatically sends personalized direct messages — so leads get an instant, relevant reply while intent is high.

Built for creators and influencers running "comment X to get Y" campaigns: drop a keyword, attach the material (link, lead magnet, offer), and let the automator deliver it via DM at scale.

---

## ✨ Features

- **💬 Comment → DM automation** — listens for new comments and triggers a DM when they match a campaign.
- **🔑 Keyword matching** — per-campaign keyword rules decide who gets messaged and what they receive.
- **📣 Campaigns & materials** — manage multiple campaigns, each with its own keywords and delivery material (links, offers, lead magnets).
- **📊 Admin dashboard** — server-rendered dashboard to manage campaigns, posts and view stats.
- **🔁 Background workers** — async DM-sender queue and a LinkedIn poller run as background tasks.
- **🪝 Webhooks + polling** — receives Instagram events via webhooks and polls LinkedIn for new activity.
- **🔐 Auth** — secure admin login with bcrypt-hashed passwords and session middleware.
- **📝 Full audit trail** — comment logs, DM logs and a DM queue persisted in the database.

---

## 🛠️ Tech Stack

| Layer        | Tech                                            |
|--------------|--------------------------------------------------|
| Framework    | FastAPI + Uvicorn                                |
| Database     | SQLAlchemy (ORM) + Pydantic Settings             |
| Auth         | passlib + bcrypt, Starlette session middleware   |
| Frontend     | Server-rendered Jinja2 templates + vanilla JS/CSS|
| HTTP         | httpx (Instagram / LinkedIn API calls)           |
| Deployment   | Docker + docker-compose (see `DEPLOY.md`)        |

---

## 🏗️ How It Works

```
Instagram/LinkedIn comment
          │
          ▼
   Webhook / Poller ──▶ Keyword Matcher ──▶ DM Queue ──▶ DM Sender (async loop)
                              │                                   │
                              ▼                                   ▼
                        Campaign rules                    Personalized DM sent
                                                          + logged (CommentLog/DMLog)
```

Core modules:
- `routers/` — webhooks, campaigns, posts, dashboard, auth, LinkedIn admin
- `services/` — `instagram.py`, `linkedin.py`, `keyword_matcher.py`, `dispatcher.py`, `url_resolver.py`
- `tasks/` — `dm_sender` and `linkedin_poller` background loops
- `models/` — Campaign, Material, InstagramPost, DMQueue, CommentLog, DMLog, User

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Instagram Graph API / LinkedIn API credentials

### Local setup

```bash
# 1. Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
#    Set ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY and your IG/LinkedIn API keys

# 3. Run
uvicorn main:app --reload      # http://localhost:8000
```

### Run with Docker

```bash
docker-compose up --build
```

> 📦 A full **free-tier deployment guide** (Oracle Cloud + Cloudflare Tunnel) is in [`DEPLOY.md`](./DEPLOY.md).

---

## ⚙️ Configuration

Key environment variables (see `.env.example`):

| Variable          | Purpose                                  |
|-------------------|------------------------------------------|
| `ADMIN_EMAIL`     | Seed admin account email                 |
| `ADMIN_PASSWORD`  | Seed admin account password              |
| `SECRET_KEY`      | Session signing key (32+ chars)          |
| Instagram / LinkedIn API keys | Platform API access          |

---

## ⚠️ Disclaimer

Use responsibly and in compliance with the **Instagram Platform Policy**, **LinkedIn API Terms** and applicable anti-spam / data-privacy regulations. Automated messaging must respect platform rules and user consent.
