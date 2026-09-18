# Build Prompt: Chrome Extension + FastAPI Backend + Third-Party Sync + Retry Queue

> Copy everything below the line into your coding agent (Claude Code, Cursor, etc.) as the initial instruction.
> Applied conventions: `cline.md` (Part A strict rules — ≤ 8-line functions, guard clauses, `is_`/`has_` booleans, no magic strings, log-and-re-raise, small reusable modules) must be passed to the agent together with this prompt.

---

## Project Goal

Build a full-stack integration for a graded assignment ("Phase 9"):

A Chrome extension (Manifest V3) lets a user highlight text or capture a page title, sends it through a popup UI to a Python backend, which:
1. Saves it locally (SQLite)
2. Mirrors it to a third-party service (Airtable)
3. If the third-party call fails, queues it for retry with exponential backoff — but the local save must still succeed regardless.

This is a graded coursework assignment. I (the human) need to be able to explain every design decision, the architecture, and any significant code in a live interview. **As you build, add short comments explaining *why*, not just what — especially in the auth logic, the retry queue, and the message-passing between content script and popup.** Do not just dump a finished solution; work in the phases below and pause after each one so I can review and understand it.

## Architecture

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

## Build Order — follow this exact sequence, do not skip ahead

Do NOT start the Chrome extension until Phase 4 (retry queue) is tested and working standalone via `curl`. The extension is just a client — it's much easier to debug once the backend is proven correct on its own.

1. **Phase 1 — Backend core** (SQLite CRUD, no auth, no third-party)
2. **Phase 2 — Auth + CORS**
3. **Phase 3 — Third-party mirror (Airtable)**
4. **Phase 4 — Retry queue + failure-test demo** (test this fully before touching the extension)
5. **Phase 5 — Chrome extension** (content script, popup, background worker)
6. **Phase 6 — End-to-end integration test**
7. **Phase 7 — README + packaging**

After each phase, stop, summarize what you built and why, and show me how to test it before moving to the next phase.

---

## Phase 1: Backend Core

Stack: **FastAPI** (preferred over Flask — mention why: async support, Pydantic validation, auto-generated OpenAPI docs, dependency injection for auth later).

Endpoints (no auth yet):
- `POST /items` — create an item (fields: `id`, `title`, `content`, `source_url`, `created_at`)
- `GET /items` — list all items
- `DELETE /items/{id}` — delete an item
- `GET /health` — returns `{"status": "ok"}`

Persistence: SQLite via a small `storage.py` module — plain `sqlite3` is fine, no need for an ORM.

Use Pydantic models for request/response validation.

Give me `curl` commands to test all four endpoints before moving to Phase 2.

## Phase 2: Auth + CORS

- Add an `X-API-Key` header requirement on all write endpoints (`POST`, `DELETE`), implemented as a FastAPI dependency (`Depends(verify_api_key)`), not inline checks in each route.
- Compare against a key stored in `.env` (`API_KEY=...`). Return `401` on mismatch or missing header.
- Add CORS middleware restricted to `chrome-extension://<EXTENSION_ID>` (read the ID from `.env` too — I won't know it until I load the extension unpacked once, so use a placeholder for now and note where I need to update it).
- **Explain in a comment**: why CORS alone is not sufficient auth (it's a browser-enforced policy; a request via `curl` or Postman ignores it entirely — that's why the API key check exists independently of CORS).

Give me updated `curl` commands, including one that demonstrates a `401` when the key is wrong or missing.

## Phase 3: Third-Party Mirror (Airtable)

- After a local SQLite save succeeds, mirror the item to an Airtable base via its REST API using a personal access token (stored in `.env` as `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`).
- Wrap the Airtable call in try/except. **A failure here must never roll back or block the local save** — that guarantee is graded explicitly.
- Give me the exact steps to create the Airtable base/table and get the token (I'll do this manually).
- Give me a `curl` test that confirms an item saved locally also appears in Airtable.

## Phase 4: Retry Queue (this is graded heavily — build it carefully)

- Add a `retry_queue` table: `id, payload (json), attempts, next_retry_at, status (pending/success/failed)`.
- When the Airtable mirror fails, enqueue the item instead of just logging the error.
- Add a background worker (an `asyncio` loop started on FastAPI startup is sufficient — no need for Celery/RQ) that:
  - Polls for due jobs (`next_retry_at <= now`)
  - Retries the Airtable call
  - On success: marks the job `success`
  - On failure: increments `attempts`, sets `next_retry_at = now + min(2^attempts, 300)` seconds (exponential backoff capped at 5 minutes)

**Failure-test deliverable — do this now, before the extension exists:**

Walk me through, step by step, a test that proves:
1. Third-party endpoint is unreachable (e.g., I'll point `AIRTABLE_BASE_ID` at something invalid, or block the domain) → `POST /items` still returns `200` and the row is in SQLite.
2. A row appears in `retry_queue` with `status=pending`.
3. When I restore the correct Airtable config, the background worker retries and the row moves to `status=success`, and the item appears in Airtable.

I need to record this as a video or annotated log for grading — give me the exact commands/steps to follow so I can capture it cleanly.

## Phase 5: Chrome Extension (Manifest V3)

Only start this after Phase 4 is verified working.

Structure:
```
extension/
  manifest.json
  content.js
  popup.html
  popup.js
  background.js
```

- `manifest_version: 3`, permissions: `["storage", "activeTab", "scripting"]`.
- **Content script**: extracts the page title and/or the user's currently selected text. Do NOT push data into the popup proactively — instead, have the popup request it when opened (`chrome.tabs.sendMessage`) and have the content script respond. **Explain in a comment why**: a content script can't reliably message a popup that isn't open yet; there's nothing listening.
- **Popup**: requests the data from the content script, displays it, and on submit POSTs to the backend with the `X-API-Key` header (store the key via `chrome.storage.local`, never `localStorage` — explain why: MV3 service workers have no DOM/window object to hang `localStorage` off of).
- **Background service worker**: minimal — MV3 doesn't support persistent background pages, so explain briefly why a service worker is used instead (event-driven, terminates when idle, restarts on events).
- Plain HTML/CSS/JS only — no SPA framework inside the extension (constraint from the assignment).
- If I want to scaffold the popup UI visually first (e.g., via Lovable), tell me what to export and how to wire the exported static files into `popup.html`/`popup.js` without pulling in a framework runtime.

## Phase 6: End-to-End Test

Give me a checklist: load the extension unpacked, copy its ID into the backend's `.env`, restart the backend, highlight text on a real page, submit via the popup, and confirm the item lands in both SQLite and Airtable.

## Phase 7: README + Secrets

- `.env.example` with placeholder values for every secret (`API_KEY`, `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_TABLE_NAME`, `EXTENSION_ID`) — never commit the real `.env`.
- `README.md` sections, in this order:
  1. Architecture diagram (reuse/adapt the ASCII one above)
  2. Setup steps — backend and extension separately
  3. API examples with `curl` for all four endpoints, including a 401 example
  4. Retry queue explanation, with the backoff formula
  5. Security considerations (API key handling, why CORS + key together, secret rotation approach)
  6. Why Airtable was chosen over the alternatives

## Deliverables Checklist

- [ ] Zipped unpacked extension folder + "Load unpacked" instructions
- [ ] Backend repo: `requirements.txt`, `.env.example`, `README.md`
- [ ] Screenshot or log proving an item written locally also appears in Airtable
- [ ] Failure-test video or annotated log (service down → local save succeeds → queued → retried → succeeds)
- [ ] `.env` NOT committed (confirm `.gitignore` includes it)

## Constraints (non-negotiable)

- Manifest V3 only — no persistent background pages.
- No SPA framework inside the extension.
- Secrets never hardcoded or committed — always via `.env`.
- Local save must succeed independent of third-party call outcome, always.

## One more thing

Before writing any code, briefly restate your plan for Phase 1 back to me so I can confirm the approach, then proceed phase by phase, pausing for my review after each one.

