# Funnel Intelligence — run the analyzer

Paste a Perspective **campaign ID** (or version ID) → get its niche, a within-niche score /100,
and recommendations. Covers ~56,500 campaigns from our analysis snapshot. Runs fully on your machine.

## Requirements
- **Python 3.10+** (3.11 or 3.12 recommended)
- ~1.5 GB free disk (the embeddings file is ~290 MB; first run also downloads a ~120 MB model)
- Internet on the *first* run only (to download the embedding model). After that it works offline.

## Setup (one time)
```bash
cd funnel-analyzer            # the unzipped folder

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run
```bash
.venv/bin/python server.py
```
Wait until it prints `serving on http://127.0.0.1:8754` (first start takes ~15–30s: it loads the
model). Then open **http://127.0.0.1:8754** in your browser, paste a campaign ID, or click an example.

To stop it: `Ctrl+C` in that terminal.

## No setup at all?
Just open **`demo.html`** by double-clicking it — a self-contained page with a set of example
funnels + the methodology. No Python needed (but it doesn't take arbitrary IDs).

## Troubleshooting
- **`Address already in use`** — a previous run is still going. Free the port and re-run:
  `lsof -ti :8754 | xargs kill -9` then `.venv/bin/python server.py`
- **First analysis is slow** — the model loads on the first request; subsequent ones are instant.
- **pip install fails on torch** — make sure you're on Python 3.10–3.12, not 3.13/3.14.

## Note
This bundle contains real (internal) Perspective funnel metadata + embeddings — keep it on
Perspective machines, don't post it publicly. It does **not** contain raw funnel copy.
