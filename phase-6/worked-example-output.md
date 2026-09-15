# Worked Example — Backend Blueprint for “StudyBuddy”

> One run of `backend-design-prompt.md` with the INPUTS filled, showing the expected output shape and quality bar. All figures below are the example’s stated assumptions, not measured facts.

## INPUTS (as filled for this run)

- **PRODUCT_IDEA:** StudyBuddy — a peer-tutoring marketplace for one university: verified student tutors publish 30-minute availability slots; students book a slot, pay per session through Stripe, and both sides rate each other after a completed session.
- **TARGET_USERS:** ~5,000 students, ~100 tutors; ~50 concurrent at peak; ~1,000 bookings/week at steady state.
- **SCALE_HORIZON:** MVP now; 10k MAU within 12 months.
- **TEAM_CONSTRAINTS:** 2 developers, Python-first, small budget, prefer managed hosting.
- **COMPLIANCE_DATA:** stores names + university emails (PII); Stripe handles cards (no card data on our servers); GDPR delete/export required.
- **INTEGRATIONS:** Stripe (payments + webhooks), transactional email, university SSO later.

---

# 1. Tech Stack

| Layer | Choice | Why (≤ 1 line) | Alternative |
|---|---|---|---|
| Language & framework | Python 3.12 + FastAPI | Async; Pydantic gives request validation + OpenAPI docs for free | Django REST (heavier batteries included) |
| API style | REST/JSON, versioned `/v1` | Simple, cacheable, team knows it | GraphQL (overkill for 2 devs) |
| Database | PostgreSQL 16 | ACID for bookings/payments; constraints + partial indexes prevent double-booking | MySQL (fine, weaker partial-index ergonomics) |
| Cache / background jobs | Redis + arq | Rate limiting, hot tutor lists, email/webhook retries | Celery + broker (more moving parts) |
| Auth tokens | JWT access 15 min + rotated refresh 7 d | Stateless reads; revocable via refresh-token store | Server sessions (fine; needs shared session store) |
| File storage | none in MVP | No user uploads at launch | S3-compatible bucket (add later) |
| Migrations | Alembic | Standard for SQLAlchemy; reviewable DDL in CI | Raw SQL scripts (no versioning/rollback) |
| Testing | pytest + Testcontainers Postgres | Real-DB tests catch constraint/race bugs | SQLite fixtures (hides PG behaviour) |
| Hosting | Fly.io (API + Redis) + managed Postgres (Neon/Render) | Cheapest managed path for a 2-dev team | AWS ECS + RDS (more control, more setup) |

# 2. Database Schema

**Entity summary.** `users` have one of three roles (`student`, `tutor`, `admin`); a tutor optionally has one `tutor_profiles` row (rate, bio, verification) and links to `subjects` through `tutor_subjects`. Tutors publish `availability_slots`; a `booking` claims exactly one slot — the core invariant is **one booking per slot**, enforced by `UNIQUE(slot_id)` on bookings plus an atomic status flip on the slot. A `payment` is 1:1 with its booking via a Stripe PaymentIntent; a `review` is 1:1 with a completed booking; `refresh_tokens` stores hashed refresh tokens so sessions can be revoked.

```sql
-- PostgreSQL 16 (StudyBuddy MVP)
CREATE TYPE user_role      AS ENUM ('student', 'tutor', 'admin');
CREATE TYPE slot_status    AS ENUM ('open', 'booked', 'blocked');
CREATE TYPE booking_status AS ENUM ('pending', 'confirmed', 'cancelled', 'completed');
CREATE TYPE payment_status AS ENUM ('pending', 'succeeded', 'refunded', 'failed');

CREATE TABLE users (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email         CITEXT       NOT NULL UNIQUE,
  password_hash TEXT         NOT NULL,                 -- argon2id
  role          user_role    NOT NULL DEFAULT 'student',
  full_name     TEXT         NOT NULL,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE tutor_profiles (
  user_id           BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  bio               TEXT    NOT NULL DEFAULT '',
  hourly_rate_cents INTEGER NOT NULL CHECK (hourly_rate_cents > 0),
  verified_at       TIMESTAMPTZ,
  rating_num        NUMERIC(3,2) NOT NULL DEFAULT 0,
  rating_count      INTEGER      NOT NULL DEFAULT 0
);

CREATE TABLE subjects (
  id   SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT    NOT NULL UNIQUE
);

CREATE TABLE tutor_subjects (
  tutor_user_id BIGINT   REFERENCES users(id)    ON DELETE CASCADE,
  subject_id    SMALLINT REFERENCES subjects(id) ON DELETE CASCADE,
  PRIMARY KEY (tutor_user_id, subject_id)
);

CREATE TABLE availability_slots (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tutor_user_id BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  starts_at     TIMESTAMPTZ NOT NULL,
  ends_at       TIMESTAMPTZ NOT NULL,
  status        slot_status NOT NULL DEFAULT 'open',
  CHECK (ends_at > starts_at AND ends_at - starts_at = INTERVAL '30 minutes'),
  UNIQUE (tutor_user_id, starts_at)                  -- no duplicate slots per tutor
);
CREATE INDEX idx_slots_tutor_time  ON availability_slots (tutor_user_id, starts_at);
CREATE INDEX idx_slots_open_window ON availability_slots (starts_at) WHERE status = 'open';

CREATE TABLE bookings (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_user_id BIGINT      NOT NULL REFERENCES users(id),
  slot_id         BIGINT      NOT NULL REFERENCES availability_slots(id),
  status          booking_status NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  cancelled_at    TIMESTAMPTZ,
  UNIQUE (slot_id)                                   -- core invariant: one booking per slot
);
CREATE INDEX idx_bookings_student ON bookings (student_user_id, created_at DESC);

CREATE TABLE payments (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  booking_id   BIGINT      NOT NULL UNIQUE REFERENCES bookings(id),
  stripe_pi_id TEXT        NOT NULL UNIQUE,          -- Stripe PaymentIntent id
  amount_cents INTEGER     NOT NULL CHECK (amount_cents > 0),
  status       payment_status NOT NULL DEFAULT 'pending',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  booking_id BIGINT   NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
  author_id  BIGINT   NOT NULL REFERENCES users(id),
  rating     SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment    TEXT     NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT        NOT NULL UNIQUE,             -- SHA-256 of the token
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ
);
CREATE INDEX idx_refresh_user ON refresh_tokens (user_id);
```

*Migrations:* Alembic; every migration ships a tested `downgrade()`; deploys run `alembic upgrade head` before the new image goes live.

# 3. API Endpoints

**Conventions.** Base path `/v1`; JSON only; errors as `{"error": {"code": "...", "message": "..."}}`; cursor pagination (`?cursor=&limit=`) on list routes; all timestamps UTC ISO-8601.

| # | Method | Path | Auth | Purpose | Request (key fields) | Success | Main errors |
|---|---|---|---|---|---|---|---|
| 1 | POST | `/v1/auth/register` | public | Create account | email, password, full_name | 201 `{user}` | 409 `email_taken` · 422 `weak_password` |
| 2 | POST | `/v1/auth/login` | public | Obtain tokens | email, password | 200 `{access, refresh}` | 401 `invalid_credentials` |
| 3 | POST | `/v1/auth/refresh` | public (refresh token) | Rotate tokens | refresh | 200 `{access, refresh}` | 401 `revoked_or_expired` |
| 4 | POST | `/v1/auth/logout` | any | Revoke refresh token | refresh | 204 | — |
| 5 | GET | `/v1/me` | any | Own profile | — | 200 `{user}` | 401 |
| 6 | PATCH | `/v1/me` | any | Update name / password | full_name? · current_password + new_password? | 200 | 403 `wrong_password` |
| 7 | GET | `/v1/subjects` | public | List subjects | — | 200 `[subject]` | — |
| 8 | GET | `/v1/tutors` | public | Search tutors | ?subject= &min_rating= &cursor= | 200 `[tutor]` | — |
| 9 | GET | `/v1/tutors/{id}` | public | Tutor profile + open slots | — | 200 | 404 |
| 10 | PUT | `/v1/tutor/profile` | tutor | Create/update rate & bio | bio, hourly_rate_cents | 200 | 403 `role_required` |
| 11 | POST | `/v1/tutor/slots` | tutor | Publish 30-min slots | slots: `[{starts_at}]` (≤ 50/req) | 201 `[slot]` | 409 `overlap` |
| 12 | DELETE | `/v1/tutor/slots/{slot_id}` | tutor (owner) | Withdraw an open slot | — | 204 | 409 `already_booked` |
| 13 | POST | `/v1/bookings` | student | Book an open slot → pending payment | slot_id (+ `Idempotency-Key` header) | 201 `{booking, stripe_client_secret}` | 409 `slot_taken` · 402 `payment_required` |
| 14 | GET | `/v1/bookings/me` | student / tutor | My bookings (either side) | ?role= &status= &cursor= | 200 `[booking]` | — |
| 15 | DELETE | `/v1/bookings/{id}` | student (owner) | Cancel ≥ 2 h before start | — | 200 `{refund: "scheduled"}` | 409 `too_late_to_cancel` |
| 16 | POST | `/v1/bookings/{id}/complete` | tutor (own session) | Mark session done (starts payout) | — | 200 | 403 `not_your_booking` · 409 `wrong_state` |
| 17 | POST | `/v1/bookings/{id}/review` | student (owner) | Review a completed session | rating 1–5, comment? | 201 | 409 `already_reviewed` |
| 18 | POST | `/v1/payments/webhook` | webhook-signature | Stripe events (succeeded / refunded) | Stripe event payload | 200 | 400 `bad_signature` (event retried by Stripe) |

*Idempotency:* #13 accepts `Idempotency-Key`; a duplicate key within 24 h returns the original booking instead of creating a second one.

# 4. Authentication & Authorization

**Flows.**
- *Register (#1):* validate email format + university domain, score password (≥ 10 chars, zxcvbn-lite ≥ 3), hash with **argon2id** (`m=64 MiB, t=3, p=4`), insert user, send verification email. MVP stance: login allowed unverified, but booking (#13) requires a verified email.
- *Login (#2):* verify argon2 hash → issue **access JWT (15 min, HS256, `kid`-tagged secret for rotation)** + **refresh token (7 d, 256-bit random; only its SHA-256 hash is stored in `refresh_tokens`)**.
- *Refresh (#3):* hash lookup → must be unrevoked and unexpired → **rotate**: old row revoked, new token issued. Presenting an already-revoked token revokes the whole token family (theft signal).
- *Logout (#4):* revoke the presented refresh token; access tokens simply expire within 15 min (accepted residual window for MVP).

**Permission matrix** (✓ = allowed, — = denied):

| Action | student | tutor | admin |
|---|:---:|:---:|:---:|
| Book a slot (#13) | ✓ | — | — |
| Cancel own booking (#15) | ✓ own | — | ✓ any |
| Publish / withdraw own slots (#11–12) | — | ✓ own | — |
| Mark session complete (#16) | — | ✓ own sessions | — |
| Review a completed session (#17) | ✓ own | — | ✓ any |
| Read any user profile (support) | — | — | ✓ |
| Issue refunds (Stripe dashboard) | — | — | ✓ |

**Abuse protections.** Rate limits (Redis): `/v1/auth/*` 5 req/min/IP, `/v1/bookings` 30 req/min/user. Login lockout: exponential backoff per account (1 → 2 → 4 → 8 min). Stripe webhook: signature verification + 5-minute timestamp tolerance + event-ID dedupe. CORS: allowlist of dashboard + marketing-site origins only. All request bodies Pydantic-validated (types, ranges, lengths); no string concatenation into SQL (ORM only).

# 5. Deployment Notes

- **Environments.** `dev` (docker-compose: Postgres + Redis + API, seed data), `staging` (Fly.io, same image, Stripe *test* keys), `prod` (Fly.io, live keys, deploy requires manual approval). Only env vars differ.
- **Hosting per component.** API: Fly.io containers (2 × shared-1x, autoscale on CPU) — cheapest managed path fitting TEAM_CONSTRAINTS. DB: managed Postgres (Neon/Render) with built-in PITR. Redis: Fly Redis (rate limits + arq queue). Background jobs: one `arq` worker process (verification emails, webhook retries, payout notifications).
- **CI/CD.** GitHub Actions on PR: `ruff` → `pytest` (Testcontainers Postgres) → build image. On merge to `main`: push image → run Alembic migrations as a pre-deploy step → rolling deploy → smoke-test `/healthz` → auto-rollback on failure.
- **Secrets & config.** All config via env vars; secrets in Fly secrets / GitHub encrypted secrets; the DB URL and JWT signing secret never appear in the repo; `kid`-tagged JWT secrets allow zero-downtime signing-key rotation.
- **Migrations-on-deploy.** Expand/contract pattern: add nullable columns and new tables first → deploy code that tolerates both shapes → remove old columns in a later release → each `downgrade()` tested in CI.
- **Backups / DR.** Managed Postgres daily snapshots + point-in-time recovery (**RPO ≤ 5 min, RTO ≤ 1 h**); Redis is rebuildable (rate limits are ephemeral).
- **Observability.** Structured JSON logs → Fly log drain; Sentry for exceptions; `/healthz` (liveness) + `/readyz` (DB ping). First three paging alerts: error rate > 2% for 5 min · p95 latency > 800 ms · any Stripe webhook failure unresolved for 15 min.
- **Scaling path (10k → 100k MAU).** At 10k: a single API replica + PgBouncer connection pooling suffices. At 100k: API replicas behind a load balancer; a read replica for tutor-search queries; move all email/webhook workloads fully into `arq`; cache hot tutor lists in Redis; consider Redis-backed token introspection.

# 6. Assumptions & Risks

**Assumptions.**
1. Stripe Connect (Express accounts) handles tutor payouts; the platform takes no cut in MVP.
2. University SSO is deferred; the university email-domain check is the only student gate at launch.
3. Sessions are in person; no video integration in MVP.
4. One currency (USD); prices are fixed per tutor (`hourly_rate_cents` per 30-min slot).
5. GDPR delete/export = hard-delete user row with cascades + anonymise bookings/payments references; export via `/v1/me` data download (added to #5 before launch).
6. No file uploads in MVP (hence no file-storage layer in §1).

**Top 3 risks.**
1. *Double-booking race* → `UNIQUE(slot_id)` plus an atomic `UPDATE availability_slots SET status='booked' WHERE id=:id AND status='open'` inside the booking transaction; the loser of the race gets `409 slot_taken`.
2. *Stripe webhook loss* → event-ID dedupe + a nightly reconciliation job comparing `payments` against Stripe PaymentIntents.
3. *Refresh-token theft* → rotation with token-family revocation + 15-min access-token window.

**Open questions for the product owner.**
1. Is the cancellation policy (full refund ≥ 2 h before start) final? It changes booking state-machine and payout timing.
2. Should admins ever read future chat/report content? That decides whether messages are end-to-end encrypted.
3. Multi-campus expansion timeline? It affects how the email-domain allowlist is designed (single domain vs table of campuses).

---

*End of worked example.* Produced by applying `backend-design-prompt.md` to the INPUTS above; the sample product is illustrative.




