# fpl-wrapped

A FastAPI-backed FPL season review service with a small interactive frontend.

## Run locally

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the app:
   ```bash
   uvicorn app:app --reload
   ```

## Configuration

- `ALLOWED_ORIGINS` — optional comma-separated list of permitted browser origins for CORS.
- `CACHE_TTL_SECONDS` — how long cached payloads should live in memory.
- `FPL_CONCURRENCY_LIMIT` — maximum concurrent requests to the FPL API.

## Deployment notes

- Use HTTPS when hosting for friends.
- Place the app behind a reverse proxy or hosting platform that supports trusted origins.
- Keep `.env` out of source control for any private configuration.
