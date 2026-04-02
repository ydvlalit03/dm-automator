# Deploy DM Automator on Oracle Cloud (Free Tier) + Cloudflare Tunnel

Total time: ~30 minutes | Cost: $0/month

---

## Step 1: Create Oracle Cloud Account

1. Go to https://cloud.oracle.com/
2. Click "Sign Up" → create a free account
3. You need a credit card for verification (you will NOT be charged)
4. Select your home region (closest to you)
5. Wait for account activation (usually instant, sometimes up to 30 min)

---

## Step 2: Create a Free ARM Instance

1. Go to Oracle Cloud Console → **Compute** → **Instances** → **Create Instance**
2. Configure:
   - **Name**: `dm-automator`
   - **Image**: Ubuntu 22.04 (or 24.04)
   - **Shape**: Click "Change Shape" → **Ampere** → **VM.Standard.A1.Flex**
     - OCPUs: `1` (free up to 4)
     - Memory: `6 GB` (free up to 24)
   - **Networking**: Use default VCN or create new
     - Make sure "Assign a public IPv4 address" is checked
   - **SSH Key**: Upload your public key or generate one
     - If generating: **Download both keys** and save them safely
3. Click **Create**
4. Wait for instance to be "Running"
5. Note down the **Public IP Address**

---

## Step 3: Open Firewall Ports

Oracle has 2 firewalls: Security List (cloud) + iptables (OS).

### 3a. Cloud Security List
1. Go to **Networking** → **Virtual Cloud Networks** → your VCN
2. Click your **Subnet** → **Security Lists** → **Default Security List**
3. Add **Ingress Rule**:
   - Source CIDR: `0.0.0.0/0`
   - Destination Port: `8000`
   - Description: `DM Automator`

### 3b. OS Firewall (do this after SSH in Step 4)
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 4: SSH into the Instance

```bash
ssh -i /path/to/your-private-key ubuntu@YOUR_PUBLIC_IP
```

---

## Step 5: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Logout and login again for group to take effect
exit
```

SSH back in:
```bash
ssh -i /path/to/your-private-key ubuntu@YOUR_PUBLIC_IP
```

Verify:
```bash
docker --version
docker compose version
```

---

## Step 6: Setup Cloudflare Tunnel

This gives you a free HTTPS URL without buying a domain.

### 6a. Create Tunnel on Cloudflare Dashboard
1. Go to https://one.dash.cloudflare.com/
2. Sign up / log in (free account is fine)
3. Go to **Networks** → **Tunnels** → **Create a tunnel**
4. Choose **Cloudflared** connector
5. Name it: `dm-automator`
6. Copy the **Tunnel Token** (long string starting with `ey...`)

### 6b. Configure Public Hostname
1. In the tunnel setup, add a **Public Hostname**:
   - If you have a domain on Cloudflare:
     - Subdomain: `dm` → Domain: `yourdomain.com`
   - If you DON'T have a domain:
     - Use Cloudflare's free `*.cfargotunnel.com` domain (auto-assigned)
2. Service: `http://app:8000`
3. Save

### 6c. Note down
- Your **Tunnel Token**
- Your **Public URL** (e.g., `https://dm.yourdomain.com` or the auto-assigned one)

---

## Step 7: Deploy the App

```bash
# Clone the repo
git clone https://github.com/lucasleadfreak-halfengi/dm-automator.git
cd dm-automator

# Create data directory
mkdir -p data

# Create .env file
cp .env.example .env
nano .env
```

### Fill in your .env:
```env
SECRET_KEY=GENERATE_A_RANDOM_STRING_HERE
ADMIN_EMAIL=your@email.com
ADMIN_PASSWORD=your-secure-password

WEBHOOK_VERIFY_TOKEN=pick-any-random-string
META_APP_SECRET=from-meta-developer-dashboard
IG_PAGE_ACCESS_TOKEN=your-long-lived-page-token
IG_BUSINESS_ACCOUNT_ID=your-ig-business-id

DATABASE_URL=sqlite:////data/dm_automator.db
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token-from-step-6
```

To generate a random SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Start everything:
```bash
docker compose up -d --build
```

### Check logs:
```bash
docker compose logs -f app
docker compose logs -f cloudflared
```

### Verify:
```bash
# Local check
curl http://localhost:8000/health

# External check (use your Cloudflare URL)
curl https://dm.yourdomain.com/health
```

---

## Step 8: Configure Meta Webhook

1. Go to https://developers.facebook.com/ → your App
2. Go to **Webhooks** → **Instagram**
3. Set Callback URL: `https://dm.yourdomain.com/webhooks/instagram`
4. Set Verify Token: same as `WEBHOOK_VERIFY_TOKEN` in your `.env`
5. Click **Verify and Save**
6. Subscribe to: `comments` field

### Activate webhook for your page:
```bash
curl -X POST "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps" \
  -d "subscribed_fields=feed" \
  -d "access_token=YOUR_PAGE_ACCESS_TOKEN"
```

---

## Step 9: Test the Full Flow

1. Open `https://dm.yourdomain.com` in browser
2. Log in with your admin credentials
3. Go to **Settings** → verify Instagram is "Connected"
4. Go to **Posts** → **Add Posts** → paste your Instagram post/reel URLs
5. Go to **Campaigns** → **New Campaign** → pick a post, set keyword, add material
6. Have someone comment the keyword on your post
7. Check **Dashboard** → DM should appear in activity feed
8. Check **DM Queue** → should show as "sent"

---

## Useful Commands

```bash
# View logs
docker compose logs -f

# Restart
docker compose restart

# Stop
docker compose down

# Update (after pushing changes to GitHub)
cd ~/dm-automator
git pull
docker compose up -d --build

# Check DB
docker compose exec app python -c "
from database import SessionLocal
from models import *
db = SessionLocal()
print('Users:', db.query(User).count())
print('Posts:', db.query(InstagramPost).count())
print('Campaigns:', db.query(Campaign).count())
print('DMs sent:', db.query(DMLog).filter(DMLog.status=='sent').count())
print('Queue:', db.query(DMQueue).filter(DMQueue.status=='queued').count())
"

# Backup DB
cp data/dm_automator.db data/backup_$(date +%Y%m%d).db
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Webhook verify fails | Check WEBHOOK_VERIFY_TOKEN matches in .env and Meta dashboard |
| DMs not sending | Check IG_PAGE_ACCESS_TOKEN is valid. Tokens expire in 60 days |
| Cloudflare tunnel not connecting | Check CLOUDFLARE_TUNNEL_TOKEN in .env. Check `docker compose logs cloudflared` |
| Health check fails | Run `docker compose logs app` to see errors |
| "Instagram not connected" | Go to Settings page and paste your tokens |
| Media ID not resolving | The post must be from YOUR Instagram Business account |
| 429 rate limit | Daily limit hit (200/day). Queue pauses automatically, resumes next day |
