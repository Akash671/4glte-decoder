---
title: 4G LTE RRC/NAS Decoder
emoji: 📡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 4G LTE RRC/NAS Decoder

[![CI](https://github.com/<your-username>/4glte-decoder/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/4glte-decoder/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

Decode raw LTE RRC and NAS hex captures (from RRC PDUs on BCCH / PCCH / CCCH / DCCH, or
bare NAS messages) into structured, human-readable JSON — built on top of
[pycrate](https://github.com/pycrate-org/pycrate).

This repo wraps a single decoder core (`app/decoder/rrc_nas_decoder.py`) with:

- **FastAPI + Pydantic** — a typed HTTP API (`app/api.py`, `app/schemas.py`)
- **Streamlit** — a browser GUI for interactive decoding (`app/streamlit_app.py`)
- **pytest** — unit tests for the decoder and the API (`tests/`)
- **GitHub Actions** — CI that lints, tests across Python 3.10–3.12, and builds the Docker image
- **Docker** — one image for the Streamlit GUI (used by Hugging Face Spaces), one for the API

## Project layout

```
.
├── app/
│   ├── decoder/
│   │   └── rrc_nas_decoder.py   # core decode logic (pycrate wrapper)
│   ├── schemas.py                # Pydantic request/response models
│   ├── api.py                    # FastAPI app
│   └── streamlit_app.py          # Streamlit GUI
├── tests/
│   ├── test_decoder.py
│   └── test_api.py
├── .github/workflows/ci.yml
├── Dockerfile                    # Streamlit GUI (Hugging Face Spaces entrypoint, port 7860)
├── Dockerfile.api                # Standalone FastAPI image (port 8000)
├── docker-compose.yml            # Run GUI + API together locally
├── requirements.txt
└── requirements-dev.txt
```

## Quickstart (local, no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Run the tests
pytest tests/ -v

# Run the API
uvicorn app.api:app --reload
# -> http://localhost:8000/docs

# Run the GUI (in another terminal)
streamlit run app/streamlit_app.py
# -> http://localhost:8501
```

## Quickstart (Docker Compose)

Runs the API and the GUI together, with the GUI calling the API over the
Docker network:

```bash
docker compose up --build
# GUI:  http://localhost:8501
# API:  http://localhost:8000/docs
```

## API usage

```bash
curl -X POST http://localhost:8000/decode \
  -H "Content-Type: application/json" \
  -d '{
        "hex_str": "0749015A4A500BF6130083000102000000015406401300830002570200001313008300012305F412345678640181",
        "layer": "NAS",
        "channel": "DCCH",
        "direction": "DL"
      }'
```

Response:

```json
{
  "ok": true,
  "layer": "NAS",
  "channel": "DCCH",
  "direction": "DL",
  "result": { "NAS_Message": { "nas_struct": { "...": "..." } } },
  "error": null
}
```

Supported `layer` / `channel` / `direction` combinations mirror the mapping in
`RRCNASDecoder.decode_universal` — see `app/schemas.py` for the exact enums,
and `GET /docs` for interactive Swagger docs once the API is running.

## Usage analytics

Both the API and GUI record lightweight usage events (page views, decode
attempts by layer/success) to a shared SQLite database via `app/analytics.py`.

- **API**: `GET /stats` returns aggregated counters as JSON.
- **GUI**: a "📊 Usage stats" panel in the sidebar shows the same counters live.

**Persistence caveat:** SQLite lives on the container's filesystem. On
Streamlit Community Cloud (and most free container hosts), that filesystem
is ephemeral -- counts survive page reloads within a session but reset on
every app restart/redeploy. For Docker/self-hosted deployments this is
solved with a named volume (already wired up in `docker-compose.yml`), so
counts survive `docker compose down`/restarts.

If you need counts that survive redeploys on a platform with no persistent
volume (e.g. plain Streamlit Cloud), swap `app/analytics.py`'s storage for a
hosted DB (Supabase's free Postgres tier is a good fit) behind the same
`record_event()` / `get_stats()` functions -- nothing else in the app needs
to change.

## Testing & CI

```bash
pytest tests/ -v --cov=app
ruff check app tests
```

`.github/workflows/ci.yml` runs the same checks on every push/PR to `main`
across Python 3.10, 3.11, and 3.12, then does a `docker build` sanity check.

## Deploying to Hugging Face Spaces

This repo is set up to deploy as a **Docker-SDK Space** running the Streamlit
GUI, decoding in-process (no separate API call needed):

1. Create a new Space at https://huggingface.co/new-space, choosing **Docker**
   as the SDK.
2. Push this repo to the Space's git remote (Spaces read `README.md`'s YAML
   front-matter above for the `sdk: docker` / `app_port: 7860` config, and
   use the root `Dockerfile` automatically):

   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git push space main
   ```

3. The Space will build the root `Dockerfile` and serve the GUI on port 7860.

If you'd rather deploy the FastAPI service separately (e.g. on Fly.io, Render,
Railway, or your own VM) and point the Space's GUI at it, build with
`Dockerfile.api` and set `DECODER_MODE=api` / `API_URL=<your API URL>` as
environment variables on the GUI deployment.

## License

This project is licensed under the [MIT License](LICENSE).

It depends on [pycrate](https://github.com/pycrate-org/pycrate) (LGPL-2.1+),
used as an unmodified library dependency — no pycrate source is vendored or
modified in this repo. If you fork this project and modify pycrate itself,
those modifications remain subject to pycrate's LGPL terms.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
the PR checklist, and a list of the highest-value things to work on. This
project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).

## Notes

- `CryptoMobile` is not installed by default, so NAS security (ciphering/
  integrity) contexts are not handled — only plaintext / unciphered NAS
  messages decode fully. Install the optional
  [`CryptoMobile`](https://github.com/P1sec/CryptoMobile) package if you need
  that.
- Decoded output can include raw bytes (e.g. inside capability containers);
  the API and GUI both convert these to hex strings before returning JSON.
