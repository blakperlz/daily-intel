# daily-intel

AI-powered intelligence aggregation platform. Bloomberg-grade financial, cyber, and geopolitical briefings delivered to your inbox — at zero cost.

## What it does

Collects signals from 10+ free data sources, summarizes them with Claude Haiku, and sends a structured HTML digest twice daily (morning + evening) plus a weekly deep dive.

**Intelligence domains:**
- Financial markets (equities, crypto, macro via yfinance + FRED)
- Cyber threats (NVD CVEs, CISA KEV, HaveIBeenPwned breaches)
- Geopolitical events (GDELT, filtered by watchlist)
- Social signals (Bluesky trending topics)
- News (Reuters, AP, Krebs, CISA advisories via RSS)
- Dark web signals (Ahmia.fi — no Tor required)

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/daily-intel.git
cd daily-intel
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

**Required:**
- `ANTHROPIC_API_KEY` — get free credits at console.anthropic.com
- `GMAIL_USER` + `GMAIL_APP_PASSWORD` — Gmail App Password (not your real password)
  - Enable at: myaccount.google.com → Security → App Passwords

**Optional (but recommended):**
- `FRED_API_KEY` — free at fred.stlouisfed.org/docs/api/api_key.html
- `HIBP_API_KEY` — free at haveibeenpwned.com/API/Key
- `NVD_API_KEY` — free at nvd.nist.gov/developers/request-an-api-key

### 3. Configure your watchlist

Edit `config.yaml`:
- Add your email(s) to `digest.recipients` (up to 5)
- Customize `collectors.geopolitical.countries` and `keywords`
- Adjust `collectors.financial.tickers`

### 4. Test it

```bash
# Dry run — prints digest JSON, no email sent
python main.py --now daily --dry

# Send a real digest immediately
python main.py --now daily
```

### 5. Start the scheduler

```bash
# Runs as a daemon — morning brief at 6am, evening at 6pm, weekly Sunday 6pm
python main.py
```

## Deploying to Oracle Cloud Always Free

```bash
# On your Oracle Cloud VM (Ubuntu 22.04, US East - Ashburn)
git clone https://github.com/YOUR_USERNAME/daily-intel.git
cd daily-intel
pip install -r requirements.txt
cp .env.example .env
# Fill in .env

# Run as a background service with nohup
nohup python main.py > logs/scheduler.log 2>&1 &

# Or use systemd (recommended for production)
# See docs/oracle-deploy.md
```

## Architecture

```
main.py
  ├── scheduler/jobs.py       APScheduler cron triggers
  └── digest_runner.py        Orchestrator
        ├── collectors/       Data sources (one file per source)
        │   ├── base.py       BaseCollector interface
        │   ├── financial.py  yfinance + FRED
        │   ├── cyber.py      NVD + CISA KEV + HIBP
        │   ├── geopolitical.py  GDELT (watchlist-filtered)
        │   ├── social.py     Bluesky public API
        │   ├── rss_news.py   RSS feeds
        │   └── dark_web.py   Ahmia.fi HTTPS proxy
        ├── llm/
        │   ├── generator.py  Claude Haiku / Gemini routing
        │   └── prompts.py    Bloomberg-style analyst prompts
        └── email/
            ├── sender.py     Gmail SMTP delivery
            └── templates/    Jinja2 HTML email (dark mode)
```

## Data sources (all free)

| Source | Domain | Auth |
|--------|--------|------|
| yfinance | Financial | None |
| FRED API | Macro | Free key |
| NVD API v2 | Cyber | None (key optional) |
| CISA KEV | Cyber | None |
| HaveIBeenPwned | Cyber/Breach | Free key |
| GDELT GKG | Geopolitical | None |
| Bluesky | Social | None |
| RSS feeds | News | None |
| Ahmia.fi | Dark web (proxy) | None |

## Roadmap

- **Phase 1 (now):** Email digest
- **Phase 2:** Self-hosted web dashboard (React + FastAPI + Docker)
- **Phase 3:** Natural language query interface (RAG + tool-use)

## License

Apache 2.0
