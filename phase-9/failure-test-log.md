# Failure-Test Log — Retry Queue (Graded Deliverable)

Recorded run of the exact test from `build-prompt.md` §Phase 4, executed
locally against `backend/mock_airtable.py` (so no real Airtable credentials
are exposed). Environment: Windows, Python 3.14, backend on `127.0.0.1:8017`,
mock Airtable on `127.0.0.1:8018` (`.env`: `AIRTABLE_API_URL=http://127.0.0.1:8018`).

## Step 1 — Airtable reachable: POST mirrors immediately

```
curl -X POST http://127.0.0.1:8017/items -H "Content-Type: application/json"
     -H "X-API-Key: demo-secret-key-123" -d "@test-payload.json"

{"title":"Interview quote","content":"Local save must never depend on the mirror",
 "source_url":"https://example.com/article","id":1,
 "created_at":"2026-09-18T02:10:18.840252Z","mirror":"mirrored"}
```

Item `id=1` is in SQLite **and** the mock Airtable accepted the record.
(The mock prints every arriving POST to its stderr, e.g.
`MOCK-AIRTABLE POST /v0/mock-base/Items HTTP/1.1" 200 -`.)

## Step 2 — Airtable goes down

```
Stop-Process -Id <mock-pid>     # mock server killed
```

## Step 3 — POST while Airtable is down: LOCAL SAVE STILL SUCCEEDS

```
curl -X POST http://127.0.0.1:8017/items -H "Content-Type: application/json"
     -H "X-API-Key: demo-secret-key-123" -d "@test-payload.json"

{"title":"Interview quote","content":"Local save must never depend on the mirror",
 "source_url":"https://example.com/article","id":2,
 "created_at":"2026-09-18T02:10:19.975797Z","mirror":"queued"}
```

HTTP **201** — the graded guarantee holds. Backend log at this moment:

```
airtable call failed: <urlopen error [WinError 10061] No connection could be
  made because the target machine actively refused it>
mirror failed for item 2, queueing: airtable call failed: <urlopen error …>
```

## Step 4 — The job is queued as pending

```
curl http://127.0.0.1:8017/queue

[{"id":1,"attempts":0,"next_retry_at":"2026-09-18T02:10:22.063335Z","status":"pending"}]
```

## Step 5 — Airtable restored: the worker retries and succeeds

```
Start-Process python mock_airtable.py 8018      # mock restarted
# (wait ~10 s: worker polls every 5 s; first retry is due after min(2^1, 300) = 2 s)

curl http://127.0.0.1:8017/queue

[{"id":1,"attempts":0,"next_retry_at":"2026-09-18T02:10:22.063335Z","status":"success"}]
```

The worker delivered the queued item to the restored Airtable (mock received
the POST) and closed the job. `attempts` stays 0 because the *first* retry
succeeded (a failing retry would show `attempts: 1, 2, …` with 2 s → 4 s → 8 s
reschedule delays).

## Step 6 — Both rows are in SQLite the whole time

```
curl http://127.0.0.1:8017/items

[{"...","id":1,...},{"...","id":2,...}]
```

## Reproduce

```powershell
cd phase-9\backend
# .env: AIRTABLE_API_URL=http://127.0.0.1:8018 (+ mock token/base/table)
.venv\Scripts\python mock_airtable.py 8018          # terminal 1
.venv\Scripts\python -m uvicorn main:app --port 8017  # terminal 2
# then POST twice, stop mock, GET /queue, restart mock, wait, GET /queue
```
