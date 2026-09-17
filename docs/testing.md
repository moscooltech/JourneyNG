# Testing

## CI execution

All tests run in **GitHub Actions** (this platform performs no builds):

- **Backend CI** → `pytest` with coverage (unit + API + security + WebSocket manager), `ruff`, `mypy`, Alembic migrations against real Postgres, Docker image build, pip-audit.
- **Mobile CI** → `flutter analyze`, `flutter test`, Android debug APK artifact.

## Backend suites

| Suite | Covers |
|---|---|
| `tests/unit/` | journey & participant state machines (terminal states, invalid transitions), location validation (ranges, NaN, accuracy, clock skew), token/password security (Argon2id format, rotation, JWT roundtrip) |
| `tests/api/` | register/login/refresh rotation/reuse-detection, full guest journey flow (create → invite → join → consent → start → upload → host view → arrive → blocked afterwards), consent-required enforcement, non-host location access blocked, stranger journey access blocked, error envelope shape, **group independence** (one arrival doesn't stop others — spec §52) |
| `tests/security/` | guest token journey scoping, forged JWT rejection, raw-token non-storage, host-only action enforcement |
| `tests/websocket/` | connection manager authorization scoping/disconnect |

## Conventions

- Tests never use real user GPS data; fixtures use synthetic Lagos coordinates.
- Backend tests run on SQLite in-memory for portability; Postgres-specific behavior is exercised in the migrations job and dockerized integration runs.
- Mocks only in tests (spec §60.15).

## Manual test protocol (spec §59 Definition of Done)

Execute the real-world scenario: host registers → creates journey → invites; visitor (guest) joins → consents → starts → locks screen/opens other apps; host sees live movement + last-updated + arrival event; sharing auto-ends on arrival; repeat with 3–5 simultaneous visitors including decline/leave/network-loss/consent-revocation/expiration/host-end cases.

## Android device matrix

Android 10–16, permission variants, battery saver, OEM restrictions, network loss/recovery — see [android-location.md](android-location.md).
