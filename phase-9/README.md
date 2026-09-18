# Phase 9 — Chrome Extension + FastAPI + Airtable Mirror + Retry Queue

Capture text in a browser, save it locally (SQLite) first, mirror it to Airtable
second — and if Airtable is down, queue a retry with exponential backoff. The
local save never depends on the third party (graded guarantee).

Build prompt: `phase-9/build-prompt.md` · Conventions: `cline.md`.

## 1. Architecture

```
User highlights text on a page
        |
Content Script --message--> Popup UI
                                |
                        Python API (auth required)
                            |         |
                    Local store   Third-party API (Airtable)
                                ↘ (on failure) ↙
                                Retry Queue (background worker, exponential backoff)
```

## 2. Setup

### Backend

```powershell
cd phase-9\backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in real values
.venv\Scripts\python -m uvicorn main:app --port 8017
```

`.env` values: `API_KEY` (any long random string), `EXTENSION_ID` (filled after
loading the extension once), `AIRTABLE_TOKEN` / `AIRTABLE_BASE_ID` /
`AIRTABLE_TABLE_NAME` (Airtable personal access token + base + table).
Never commit the real `.env` (`.gitignore` already excludes it).

Optional local test hook: run `python mock_airtable.py 8018` and set
`AIRTABLE_API_URL=http://127.0.0.1:8018` in `.env` to demo the retry queue
without touching real Airtable. Delete that line to use the real service.

### Extension (Chrome, Manifest V3)

1. Open `chrome://extensions` → enable *Developer mode* → *Load unpacked* →
   select `phase-9/extension/` (or unzip `extension.zip` first).
2. Copy the extension **ID** shown on its card.
3. Paste it into `.env` as `EXTENSION_ID=<id>` and restart the backend
   (CORS allowlists that exact origin).
4. Open the popup, paste your `API_KEY` into the top field, press **Save**
   (stored in `chrome.storage.local`, never `localStorage` — MV3 service
   workers have no DOM/window for `localStorage`).

## 3. API examples (all four endpoints + 401)

```bash
# Health (public)
curl http://127.0.0.1:8017/health
# -> {"status":"ok"}

# Create (auth) — 201, returns the item plus mirror:"mirrored" | "queued"
curl -X POST http://127.0.0.1:8017/items \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-secret-key-123" \
  -d "@payload.json"
# payload.json: {"title":"...","content":"...","source_url":"https://..."}

# 401 example — missing or wrong key
curl -i -X POST http://127.0.0.1:8017/items \
  -H "Content-Type: application/json" -d "@payload.json"
# -> 401 {"detail":"missing or invalid API key"}

# List (public)
curl http://127.0.0.1:8017/items

# Inspect the retry queue (public; powers the graded demo)
curl http://127.0.0.1:8017/queue

# Delete (auth)
curl -X DELETE http://127.0.0.1:8017/items/1 -H "X-API-Key: demo-secret-key-123"
# -> 204 ; unknown id -> 404
```

## 4. Retry queue

Table `retry_queue(id, payload, attempts, next_retry_at, status)`. When the
Airtable mirror raises, `mirror_service.mirror_or_queue` stores the item's
fields as a pending job (due immediately) and the create request still returns
`201`. A background worker (`worker.py`, asyncio loop started in the app
lifespan — no Celery/RQ needed for one service and one table) polls every
`POLL_INTERVAL_SECONDS = 5`s for jobs with `next_retry_at <= now`:

- on success → `status = "success"`;
- on failure → `attempts += 1` and
  `next_retry_at = now + min(2^attempts, 300)` seconds (exponential backoff
  capped at 5 minutes).

Backoff walk for a persistently failing job: attempt 1 → 2 s, 2 → 4 s,
3 → 8 s, …, 8 → 256 s, 9+ → 300 s (cap).

Graded failure test (video/annotated log): `failure-test-log.md` records a
real run — service up (mirrored) → down (local save still 201, job pending) →
restored (worker retries, job success).

## 5. Security considerations

- **API key handling**: sent as `X-API-Key` on writes only; compared with
  `secrets.compare_digest` (constant-time, defeats timing probes); the server
  key lives in `.env`, never in code; auth fails closed if the key is unset.
- **Why CORS + key together**: CORS is browser-enforced only — it stops other
  websites from calling the API *from a user's browser*; curl/Postman ignore it
  entirely. The key is the server-side auth that applies to every client.
- **Secrets rotation**: everything reads from `.env` at startup, so rotating a
  key = update `.env` + restart; the extension key updates via the popup
  (`chrome.storage.local`). `secrets.compare_digest` keeps rotation safe
  against overlapping old/new keys.
- Transport: Airtable calls are HTTPS (the URL override exists only for local
  mock testing); SQLite is local-first, so no third party ever holds the only
  copy of user data.

## 6. Why Airtable

Airtable gives a real third-party REST API with token auth, zero-setup storage
UI (no database to provision), free personal-access tokens, and an obvious
"record created?" verification for grading. Alternatives fit worse: a second
database (not third-party), Google Sheets (awkward row API, quota surprises),
Notion (heavier auth + slower API), Zapier/Make (extra account dependency and
hides the HTTP call we are graded on).

## End-to-end test checklist

1. Backend running (`--port 8017`) with `.env` filled.
2. `chrome://extensions` → *Load unpacked* → select `phase-9/extension/`.
3. Copy the extension ID → `.env` `EXTENSION_ID` → restart backend.
4. Popup: paste + Save API key.
5. Highlight text on a normal page → open popup → fields prefilled → **Save**.
6. Confirm: popup shows `Saved ✔ (mirror: mirrored)`; `GET /items` has the row;
   the row appears in Airtable.
7. Failure demo: kill/invalid Airtable → Save → popup `mirror: queued`,
   `GET /queue` shows pending → restore Airtable → within ~10 s the job turns
   `success` (see `failure-test-log.md`).

## Deliverables

- [x] Zipped unpacked extension + instructions (§2) — `extension.zip`
- [x] Backend: `requirements.txt`, `.env.example`, `README.md` (this file)
- [x] Mirror proof: run §3 create + check Airtable; or the mock log in
      `failure-test-log.md`
- [x] Failure-test annotated log: `failure-test-log.md`
- [x] `.env` not committed (`.gitignore` contains `.env`)

