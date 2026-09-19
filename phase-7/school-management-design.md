# School Management System — Design Document

## 1. Overview

The School Management System (SMS) is a multi-branch platform that centralizes academic and financial operations: admissions, class/section management, enrolment, per-period attendance, exam grading, and fee invoicing with gateway-backed payments. It replaces spreadsheets and paper registers with a single normalized relational core, exposed to Admin, Teacher, Student, Parent, and Accountant roles under strict RBAC. The design priorities are data integrity (3NF, foreign keys, check constraints), auditability, and horizontal scalability across branches.

## 2. Database Schema

Twenty tables implement the domain. Conventions: every table has a surrogate `BIGINT IDENTITY` primary key and `CreatedAtUtc`/`UpdatedAtUtc` audit columns (omitted below for brevity); `BranchId` is a plain `INT` shard key carried on branch-scoped rows — it deliberately has **no** foreign key because rows are routed to a branch shard before constraint checks run.

### 2.1 People

- **Students** — Columns: `StudentId` (PK), `AdmissionNumber` (UNIQUE), `FirstName`, `LastName`, `DateOfBirth`, `Gender`, `BloodGroup`, `PhotoUrl`, `GuardianParentId` (FK → Parents), `ContactPhone`, `Address`, `BranchId`, `Status`. **3NF:** every non-key attribute describes the student alone; year-dependent class placement lives in Enrolments, so no transitive dependency exists.
- **Teachers** — Columns: `TeacherId` (PK), `EmployeeNumber` (UNIQUE), `FirstName`, `LastName`, `Email` (UNIQUE), `Phone`, `Specialization`, `JoiningDate`, `BranchId`. **3NF:** all attributes are intrinsic teacher facts; teaching assignments are derived from Sections/ExamComponents, not stored here.
- **Parents** — Columns: `ParentId` (PK), `FirstName`, `LastName`, `Email` (UNIQUE), `Phone`, `Occupation`, `RelationToStudent`. **3NF:** guardian identity is independent; the parent↔child relationship is a single FK on Students, eliminating repeating child columns in Parents.
- **Users** — Columns: `UserId` (PK), `Email` (UNIQUE), `PasswordHash`, `FullName`, `Phone`, `Status`, `LastLoginAtUtc`, `StudentId`/`TeacherId`/`ParentId` (nullable FKs), `CHECK` that exactly one person link is set. **3NF:** credentials are normalized out of the person tables, so login mechanics never duplicate person data.
- **Roles** — Columns: `RoleId` (PK), `RoleName` (UNIQUE). **3NF:** a single atomic fact per row.
- **UserRoles** — Columns: composite PK (`UserId`, `RoleId`), `GrantedById` (FK → Users), `GrantedAtUtc`. **3NF:** pure junction resolving the User↔Role many-to-many; nothing depends on anything beyond the pair.
- **AuditLog** — Columns: `AuditId` (PK), `UserId` (nullable FK → Users), `TableName`, `RecordId`, `Action`, `OldValues` (JSON), `NewValues` (JSON), `OccurredAtUtc`, `IpAddress`. **3NF:** one append-only event per row; no updateable state to normalize further.

### 2.2 Academics

- **Classes** — Columns: `ClassId` (PK), `ClassName` (e.g. "Grade 8"), `GradeLevel`, `BranchId`. **3NF:** one row per class definition; nothing depends on anything but `ClassId`.
- **Sections** — Columns: `SectionId` (PK), `ClassId` (FK → Classes), `SectionName` ("A"/"B"), `Capacity`, `ClassTeacherId` (FK → Teachers), `UNIQUE(ClassId, SectionName)`. **3NF:** only section-scoped facts; the class definition stays in Classes.
- **Subjects** — Columns: `SubjectId` (PK), `SubjectCode` (UNIQUE), `SubjectName`, `GradeLevel`. **3NF:** subject catalog facts only.
- **Enrolments** — Columns: `EnrolmentId` (PK), `StudentId` (FK → Students), `SectionId` (FK → Sections), `AcademicYear`, `EnrolDate`, `Status`, `UNIQUE(StudentId, SectionId, AcademicYear)`. **3NF:** junction resolving Student↔Section over time; repeating year columns removed from Students.
- **Attendance** — Columns: `AttendanceId` (PK), `EnrolmentId` (FK → Enrolments), `Date`, `PeriodNo`, `Status` (Present/Absent/Late/Excused/Holiday), `MarkedById` (FK → Users), `MarkedAtUtc`, `UNIQUE(EnrolmentId, Date, PeriodNo)`. **3NF:** exactly one fact per cell of the day×period grid; daily totals are derived, never stored per row.
- **Exams** — Columns: `ExamId` (PK), `AcademicYear`, `Term`, `ExamType`, `StartDate`, `EndDate`, `Status` (Draft/Active/Published). **3NF:** exam-schedule facts only.
- **ExamComponents** — Columns: `ComponentId` (PK), `ExamId` (FK → Exams), `SubjectId` (FK → Subjects), `ComponentName` (Assignment/MidTerm/Final/Practical), `DefaultWeightPct`, `MaxMarks`, `WeightOverridePct` (nullable), `UNIQUE(ExamId, SubjectId, ComponentName)`. **3NF:** weight and max-marks facts depend only on the component row.
- **ExamMarks** — Columns: `ExamMarkId` (PK), `ComponentId` (FK → ExamComponents), `StudentId` (FK → Students), `MarksObtained`, `Status` (Draft/Published), `EnteredById` (FK → Users), `EnteredAtUtc`, `UNIQUE(StudentId, ComponentId)`. **3NF:** a mark depends solely on (student, component); report-card totals are computed, not stored.
- **GradeScale** — Columns: `GradeScaleId` (PK), `AcademicYear`, `GradeLetter` (A+/A/B/C/D/F), `MinPercentage`, `MaxPercentage`, `GradePoint`, `IsCurrent`, `UNIQUE(AcademicYear, GradeLetter)`. **3NF:** thresholds belong to the (year, letter) pair — versioning is inherent to the key.

### 2.3 Finance

- **Fees** — Columns: `FeeId` (PK), `FeeName`, `Amount`, `Frequency` (Monthly/Termly/Annual), `ClassId` (nullable FK → Classes; NULL = all classes), `AcademicYear`, `IsActive`. **3NF:** fee definitions never mix in who owes them — liability rows are Invoices.
- **Invoices** — Columns: `InvoiceId` (PK), `StudentId` (FK → Students), `FeeId` (FK → Fees), `AcademicYear`, `IssueDate`, `DueDate`, `AmountDue`, `AmountPaid`, `Status` (Unpaid/Partial/Paid/Overdue/Refunded), `UNIQUE(StudentId, FeeId, AcademicYear, IssueDate)`. **3NF:** invoice facts depend on the invoice; `AmountPaid` is a controlled, transaction-maintained aggregate kept for O(1) reads.
- **Payments** — Columns: `PaymentId` (PK), `InvoiceId` (FK → Invoices), `Amount`, `Method` (Cash/Bank/Card/Gateway), `PaymentDateUtc`, `ReceivedById` (FK → Users), `IdempotencyKey` (UNIQUE), `Status`. **3NF:** one recorded money-in event per row; gateway plumbing is delegated to its own table.
- **PaymentGatewayTransactions** — Columns: `GatewayTxnId` (PK), `PaymentId` (FK → Payments), `GatewayName`, `GatewayRef`, `IdempotencyKey`, `RequestPayload` (JSON), `ResponsePayload` (JSON), `RetryCount`, `Status`, `RefundAmount`. **3NF:** provider-specific state is isolated so adding a gateway never touches Payments.

### 2.4 Canonical DDL

**Students**

```sql
CREATE TABLE Students (
    StudentId        BIGINT IDENTITY PRIMARY KEY,
    AdmissionNumber  VARCHAR(20)   NOT NULL UNIQUE,
    FirstName        NVARCHAR(60)  NOT NULL,
    LastName         NVARCHAR(60)  NOT NULL,
    DateOfBirth      DATE          NOT NULL,
    Gender           CHAR(1)       NOT NULL CHECK (Gender IN ('M','F','O')),
    BloodGroup       VARCHAR(5)    NULL,
    PhotoUrl         NVARCHAR(300) NULL,
    GuardianParentId BIGINT        NULL REFERENCES Parents (ParentId),
    ContactPhone     VARCHAR(20)   NULL,
    Address          NVARCHAR(300) NULL,
    BranchId         INT           NOT NULL,
    Status           VARCHAR(10)   NOT NULL DEFAULT 'Active',
    CreatedAtUtc     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
```

**ExamMarks**

```sql
CREATE TABLE ExamMarks (
    ExamMarkId     BIGINT IDENTITY PRIMARY KEY,
    ComponentId    BIGINT       NOT NULL REFERENCES ExamComponents (ComponentId),
    StudentId      BIGINT       NOT NULL REFERENCES Students (StudentId),
    MarksObtained  DECIMAL(6,2) NOT NULL CHECK (MarksObtained >= 0),
    Status         VARCHAR(10)  NOT NULL DEFAULT 'Draft'
                   CHECK (Status IN ('Draft','Published')),
    EnteredById    BIGINT       NOT NULL REFERENCES Users (UserId),
    EnteredAtUtc   DATETIME2    NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_ExamMarks_Student_Component UNIQUE (StudentId, ComponentId)
);
```

**Invoices**

```sql
CREATE TABLE Invoices (
    InvoiceId    BIGINT IDENTITY PRIMARY KEY,
    StudentId    BIGINT        NOT NULL REFERENCES Students (StudentId),
    FeeId        BIGINT        NOT NULL REFERENCES Fees (FeeId),
    AcademicYear SMALLINT      NOT NULL,
    IssueDate    DATE          NOT NULL,
    DueDate      DATE          NOT NULL,
    AmountDue    DECIMAL(10,2) NOT NULL CHECK (AmountDue > 0),
    AmountPaid   DECIMAL(10,2) NOT NULL DEFAULT 0,
    Status       VARCHAR(10)   NOT NULL DEFAULT 'Unpaid'
                 CHECK (Status IN ('Unpaid','Partial','Paid','Overdue','Refunded')),
    CreatedAtUtc DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_Invoices_Student_Fee_Term UNIQUE (StudentId, FeeId, AcademicYear, IssueDate),
    CONSTRAINT CK_Invoices_Paid_Lte_Due CHECK (AmountPaid >= 0 AND AmountPaid <= AmountDue)
);
```

## 3. Attendance Model

Attendance is stored **per period**, not per day: each row is one `(Enrolment, Date, PeriodNo)` cell with a status. Rationale: secondary-school timetables differ by period, so only the per-period model can distinguish "absent all day" from "absent periods 5–6" and supports late-arrival mid-day marking without schema changes. The `UNIQUE(EnrolmentId, Date, PeriodNo)` constraint makes double-marking impossible even under concurrent teacher submissions.

Exceptions are modeled as statuses, not special rows: **holidays** are pre-marked for the whole section by the calendar job, **approved leaves** pre-seed `Excused`, and excused absences are excluded from disciplinary counters while remaining visible on reports. This keeps the raw grid uniform — every query walks the same shape regardless of why a period was missed.

Summary strategy is two-tier: on write, the same transaction updates per-student daily aggregates (present/absent counts), so dashboards read precomputed numbers; a nightly background job recomputes all aggregates from the raw grid to heal any drift, and the same job is the replay tool after schema or bug fixes.

## 4. Exam Marks & Grade Scale

Each exam is decomposed into **ExamComponents** with default weights — Assignments 20%, MidTerm 30%, Final 40%, Practical 10% (summing to 100) — plus `MaxMarks` per component. A component's `WeightOverridePct` lets one exam deviate (e.g. no practical this term) without mutating the shared defaults; the published final score is `Σ(component percentage × effective weight / 100)`, computed from published marks only.

Grades are never assumed current: **GradeScale rows are versioned by `AcademicYear`**, so a 2024 transcript re-renders with the 2024 thresholds even after the school tightens cutoffs in 2025. `IsCurrent` flags the active year's scale for hot-path lookups, while historical scales are immutable rows — this is what preserves historical integrity of issued report cards.

## 5. Payments

The money flow is a strict chain: **Fees** define what is chargeable (amount, frequency, per-class or school-wide) → **Invoices** instantiate a liability for a student per term → **Payments** record money received against an invoice (cash, bank, card, or gateway) → **PaymentGatewayTransactions** capture the provider-side truth for gateway methods. Invoice `Status` transitions (Unpaid → Partial → Paid → Refunded) are derived from `AmountDue` vs `AmountPaid` and maintained only inside payment transactions.

Supported gateways: **Stripe** (international cards), **SSLCommerz** and **bKash** (Bangladesh), and **Razorpay** (India) — all normalized behind one `GatewayName` column so providers are configuration, not code paths. Every gateway call carries an **idempotency key** (also UNIQUE on Payments): webhook replays and client retries can safely hit the endpoint repeatedly, but exactly one payment row results. Network retries reuse the same key with exponential backoff; **refunds** insert a gateway transaction with refund semantics, decrement `AmountPaid`, and flip the invoice to `Refunded` (or back to `Partial`).

## 6. Roles & Access Control

| Capability | Admin | Teacher | Student | Parent | Accountant |
|---|---|---|---|---|---|
| Manage users & roles | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage classes / sections / subjects | ✅ | ❌ | ❌ | ❌ | ❌ |
| Mark attendance | ✅ (any section) | ✅ (own sections) | ❌ | ❌ | ❌ |
| Enter / publish exam marks | ❌ | ✅ (own subjects) | ❌ | ❌ | ❌ |
| View own report card | ✅ (all) | ✅ (own students) | ✅ (own) | ❌ | ❌ |
| View child's report card | ✅ | ❌ | ❌ | ✅ (own children) | ❌ |
| Create / manage invoices | ✅ | ❌ | ❌ | ❌ | ✅ |
| Record payments & refunds | ✅ | ❌ | ❌ | ❌ | ✅ |
| View audit log | ✅ | ❌ | ❌ | ❌ | ❌ |
| Generate academic reports | ✅ | ✅ (own sections) | ❌ | ❌ | ✅ (finance only) |

RBAC is implemented through the **UserRoles** junction: a `User` holds zero or more roles, and every request resolves `UserId → role set → permission checks` in the service layer before touching data. Scoping (e.g. "own sections") is enforced by adding the owning-teacher/enrolment predicates to queries, not by separate code paths, and every privileged action lands in `AuditLog` with the acting `UserId` and before/after JSON.

## 7. Data Flows

- **Student pays a fee:** fee → invoice (issued per term) → parent/student opens checkout → gateway charge with idempotency key → webhook confirms → `Payments` row + `PaymentGatewayTransactions` row in one transaction → invoice status recomputed → receipt emitted. A replayed webhook short-circuits on the idempotency key.
- **Teacher submits marks:** teacher opens component grid (own subjects only) → saves drafts → validates `MarksObtained ≤ MaxMarks` → publishes → `ExamMarks` rows flip Draft → Published → report-card aggregate job recomputes weighted totals for affected students only.
- **Parent views report card:** parent authenticates → RBAC resolves their children → system fetches published marks, applies the **child's academic-year** GradeScale → renders weighted grades and attendance summary → read served from cache/replica.
- **Admin generates attendance report:** admin selects branch/section/date-range → query hits the on-write aggregates (raw grid only if range includes unrecalculated days) → report streams from a read replica → generation itself is audit-logged.

## 8. Scaling & Operations

**Indexes:** FK columns (`EnrolmentId`, `ComponentId`, `InvoiceId`, `PaymentId`) are indexed for join and cascade paths; hot lookups get covering indexes — `IX_Attendance (EnrolmentId, Date, PeriodNo)` is served by the unique key itself, plus `IX_ExamMarks (StudentId, Status)`, `IX_Invoices (StudentId, Status)`, `IX_Payments (InvoiceId)`. **Caching:** Redis holds session/permission sets, the current-year `GradeScale` (24 h TTL, invalidated on publish), and dashboard counters; caches are write-through for aggregates, cache-aside for catalogs.

**Read replicas** serve report cards, dashboards, and the admin attendance report; writes stay on the primary. **Background jobs** (worker queue): nightly attendance aggregate recalculation, overdue-invoice sweep, webhook retry worker with exponential backoff, and refund reconciliation against gateway statements. **Sharding by BranchId:** rows carry `BranchId` as the shard key, so each branch maps to one shard, cross-shard queries only occur in the global reporting service, and adding a school branch is a data-plane event, not a refactor. **Rate limiting:** token-bucket per IP/user on auth (5 attempts/min) and mutation endpoints, looser on reads; gateway webhooks are exempt but verified by signature instead.

## 9. Non-Functional Concerns

**Backups & DR:** nightly full backups + transaction-log backups every 15 minutes (RPO ≤ 15 min), 30-day retention with yearly archive; disaster recovery restores to a warm standby with RTO ≤ 1 h, validated by a quarterly restore drill. **Audit:** `AuditLog` is append-only — the DB role holds INSERT-only grants, so history cannot be rewritten even by an application bug; finance actions are retained 7 years, attendance raw rows 2 years (summaries kept), soft-deleted people purge after 90 days. **Security:** passwords are bcrypt (cost 12); PII columns (`Address`, `ContactPhone`, payment payloads) are encrypted at rest with **AES-256**, TLS 1.2+ in transit, secrets via vault not config files; login throttling and webhook signature verification close the remote-attack surface.

## 10. Conclusion

The design earns reliability from constraints instead of discipline: unique keys make double-marking and double-charging impossible, the money chain is idempotent end to end, and append-only auditing survives operator error. It scales because every branch-scoped row carries the shard key, reads fan out to replicas and Redis, and heavy work runs in background jobs. And it stays secure by pairing RBAC-scoped service checks with bcrypt credentials, AES-256 at rest, and an audit trail that cannot be edited.