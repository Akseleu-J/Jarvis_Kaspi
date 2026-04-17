.PHONY: install run worker beat lint fmt migrate

install:
	pip install -r requirements.txt
	playwright install chromium

run:
	cd app && python main.py

worker:
	celery -A infrastructure.tasks.celery_app worker \
	  --loglevel=info \
	  --queues=scraping,maintenance \
	  --concurrency=4

beat:
	celery -A infrastructure.tasks.celery_app beat \
	  --loglevel=info

lint:
	ruff check .
	mypy . --ignore-missing-imports

fmt:
	ruff format .

test:
	pytest tests/ -v --asyncio-mode=auto

docker-up:
	docker compose up -d redis

docker-down:
	docker compose down
