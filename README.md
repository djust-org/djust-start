# djust-start

Minimal opinionated starter for [djust](https://djust.org) — from `git clone` to a running app in under 2 minutes.

[![Deploy to djustlive](https://img.shields.io/badge/deploy_to-djustlive-E57324?style=flat-square)](https://djustlive.com)

**Requires:** Python 3.12+, [uv](https://docs.astral.sh/uv/), make

## 1. Clone and install

```bash
git clone https://github.com/djust-org/djust-start.git myapp
cd myapp
```

## 2. Run

```bash
make install
make dev
```

`make install` creates `.venv`, installs deps, and generates `.env` with a random `SECRET_KEY`. `make dev` migrates and starts the server on `:8000`.

Visit [http://localhost:8000](http://localhost:8000) — you should see a welcome page with a live counter.

## 3. Deploy to djustlive

Ship this app to a live HTTPS URL in seconds — no servers to manage.

Sign up at [djustlive.com](https://djustlive.com) and create a project, then:

```bash
.venv/bin/djust deploy login        # one-time: authenticate the CLI
.venv/bin/djust deploy <your-slug>  # deploy this directory (or: make deploy)
```

Your app goes live at `https://<your-slug>.djustlive.app`. Check status any time
with `djust deploy status`, and add your own custom domain from the dashboard.

## 4. Next steps

- Add views in `apps/home/views.py` or create a new app under `apps/`
- Register new view modules in `config/settings/base.py` → `LIVEVIEW_ALLOWED_MODULES`
- Switch to `config/settings/prod.py` in production via `DJANGO_SETTINGS_MODULE=config.settings.prod`
- [docs.djust.org/getting-started](https://docs.djust.org/getting-started/) — full guide
