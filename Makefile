# Load .env into the environment if it exists.
ifneq (,$(wildcard .env))
    include .env
    export
endif

VENV := .venv
PY   := $(VENV)/bin/python

.PHONY: dev test test-verbose migrate makemigrations lint format typecheck shell superuser check venv install collectstatic deploy

venv:
	python3 -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install uv
	$(VENV)/bin/uv pip install -e ".[dev]"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		python3 -c "import secrets; key=secrets.token_urlsafe(50); data=open('.env').read(); open('.env','w').write(data.replace('SECRET_KEY=changeme','SECRET_KEY='+key))"; \
		echo "Created .env with a generated SECRET_KEY"; \
	fi

dev:
	$(PY) manage.py migrate --run-syncdb
	@# NOTE: NO --reload here. uvicorn --reload restarts the worker on
	@# file save, dropping LiveView WebSocket state — symptom: the page
	@# flashes the new design then snaps back to the old one as the
	@# client reconnects against cached old VDOM. djust's Hot View
	@# Replacement (HVR) auto-enables when DEBUG=True and watchdog is
	@# installed (in [project.optional-dependencies].dev) and preserves
	@# form input, scroll position, and view state across reloads.
	@# Look for "[HotReload] Hot reload enabled..." in startup logs.
	$(VENV)/bin/uvicorn config.asgi:application --host 0.0.0.0 --port 8000

test:
	$(VENV)/bin/pytest

test-verbose:
	$(VENV)/bin/pytest -v

migrate:
	$(PY) manage.py migrate

makemigrations:
	$(PY) manage.py makemigrations

lint:
	$(VENV)/bin/ruff check .

format:
	$(VENV)/bin/ruff format .

typecheck:
	$(VENV)/bin/mypy

shell:
	$(PY) manage.py shell

superuser:
	$(PY) manage.py createsuperuser

check:
	$(PY) manage.py check

collectstatic:
	$(PY) manage.py collectstatic --noinput

deploy:
	$(VENV)/bin/djust deploy
