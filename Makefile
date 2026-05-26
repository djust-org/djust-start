# Load .env into the environment if it exists.
ifneq (,$(wildcard .env))
    include .env
    export
endif

VENV := .venv
PY   := $(VENV)/bin/python

.PHONY: dev test test-verbose migrate makemigrations lint format shell superuser check venv install collectstatic

venv:
	python3 -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install uv
	$(VENV)/bin/uv pip install -e ".[dev]"

dev:
	$(PY) manage.py migrate --run-syncdb
	$(VENV)/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application

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

shell:
	$(PY) manage.py shell

superuser:
	$(PY) manage.py createsuperuser

check:
	$(PY) manage.py check

collectstatic:
	$(PY) manage.py collectstatic --noinput
