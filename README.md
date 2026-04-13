# 🤖 Kaspi Search Bot

Production-grade Telegram bot for searching products on Kaspi.kz with AI-powered intent extraction.

Built with **Clean Architecture**, **SOLID**, and **DDD** principles.

---

## ✨ Features

- 🔍 Smart product search on Kaspi.kz via Playwright scraper
- 🧠 Google Gemini AI for intent extraction and chat
- 💬 Context-aware conversation memory (Redis)
- ⚡ Rate limiting, error handling, structured logging
- 🗄️ PostgreSQL (Neon.tech) + SQLAlchemy 2.0 async
- 🔄 Celery workers for heavy background scraping
- ⏰ APScheduler for scheduled tasks
- 🛡️ Circuit breaker pattern on scraper

---

## 🏗️ Architecture

```
Presentation Layer  →  Telegram handlers, middlewares
Application Layer   →  Services, use cases
Domain Layer        →  Entities, repository interfaces
Infrastructure      →  DB, Redis, Gemini, Playwright
```

---

## 📁 Project Structure

```
app/
  main.py                    # Entrypoint
core/
  config.py                  # Pydantic settings
  logger.py                  # Structured JSON logging
  container.py               # Dependency injection
domain/
  entities/                  # User, Product
  interfaces/                # Abstract repositories
application/
  services/                  # GeminiService, SearchService, UserService
infrastructure/
  db/                        # SQLAlchemy models, session
  cache/                     # Redis client
  external/                  # Gemini client, Kaspi scraper
  repositories/              # Concrete repository implementations
  tasks/                     # Celery tasks, APScheduler
presentation/
  handlers/                  # Telegram message handlers
  middlewares/               # Logging, RateLimit, Error
```

---

## ⚙️ Tech Stack

| Component | Technology |
|---|---|
| Bot framework | aiogram 3.x |
| Database | PostgreSQL (Neon.tech) + SQLAlchemy 2.0 |
| Cache / FSM | Redis |
| AI | Google Gemini 2.0 Flash |
| Scraping | Playwright (async) |
| Background jobs | Celery + Redis |
| Scheduler | APScheduler |
| Logging | structlog (JSON) |

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your_username/kaspi-search-bot.git
cd kaspi-search-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

Fill in required values:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:pass@host/db?statement_cache_size=0
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run

```bash
export PYTHONPATH=$(pwd)
python app/main.py
```

### 4. Run Celery worker (optional, for heavy scraping)

```bash
celery -A infrastructure.tasks.celery_app worker --loglevel=info --queues=scraping,maintenance
```

---

## 🖥️ VPS Deployment (systemd)

```bash
# Copy service files
cp deploy/tg_bot.service /etc/systemd/system/
cp deploy/tg_bot_worker.service /etc/systemd/system/

# Enable and start
systemctl daemon-reload
systemctl enable tg_bot tg_bot_worker
systemctl start tg_bot tg_bot_worker

# Check logs
journalctl -u tg_bot -f
```

---

## 🐳 Docker

```bash
docker compose up -d
```

---

## 🧪 Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v --asyncio-mode=auto
```

---

## 📝 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather | ✅ |
| `DATABASE_URL` | PostgreSQL async connection string | ✅ |
| `REDIS_URL` | Redis connection string | ✅ |
| `GEMINI_API_KEY` | Google AI Studio API key | ✅ |
| `RATE_LIMIT_REQUESTS` | Max requests per window (default: 10) | ❌ |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds (default: 60) | ❌ |
| `LOG_LEVEL` | Logging level (default: INFO) | ❌ |

---

## 📄 License

MIT
