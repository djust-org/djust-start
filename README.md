# djust-start

Minimal opinionated starter for [djust](https://djust.org) — from `git clone` to a running app in under 2 minutes.

## 1. Clone and rename

```bash
git clone https://github.com/djust-org/djust-start.git myapp
cd myapp
```

Rename `project/` to your project name, then update the three references to it:

```bash
mv project myapp
# In manage.py, myapp/asgi.py, myapp/wsgi.py:
#   replace "project.settings" → "myapp.settings"
#   replace "project.asgi"     → "myapp.asgi"   (in asgi.py)
```

## 2. Configure

```bash
cp .env.example .env
```

Generate a secret key and set it in `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

`DATABASE_URL` and `DJUST_STATE_BACKEND` are blank by default — SQLite and in-memory state work fine for local dev, no changes needed.

## 3. Run

```bash
make install   # create .venv and install deps
make dev       # migrate + start server on :8000
```

Visit [http://localhost:8000](http://localhost:8000) — you should see a welcome page with a live counter.

## 4. Next steps

- Add views in `apps/home/views.py` or create a new app under `apps/`
- Register new view modules in `project/settings.py` → `LIVEVIEW_ALLOWED_MODULES`
- [docs.djust.org/getting-started](https://docs.djust.org/getting-started/) — full guide
