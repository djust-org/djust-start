# djust-start

Minimal opinionated starter for [djust](https://djust.org) — from `git clone` to a running app in under 2 minutes.

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

## 3. Next steps

- Add views in `apps/home/views.py` or create a new app under `apps/`
- Register new view modules in `config/settings.py` → `LIVEVIEW_ALLOWED_MODULES`
- [docs.djust.org/getting-started](https://docs.djust.org/getting-started/) — full guide
