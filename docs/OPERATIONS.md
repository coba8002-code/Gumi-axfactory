# Pilot operations

## Start

Python 3.12+, PostgreSQL 16, Docker Compose. This independent stack does not access ERP/MES.
Copy .env.example to .env and populate credentials **locally**:

- POSTGRES_PASSWORD: randomly generated database password.
- DATABASE_URL: postgresql://factory:<URL-encoded-password>@db:5432/factory
- Optional REPORT_TOKEN: separately provisioned supervisor token.
- Optional REPORT_SENSOR_ID: the single main meter for automatic reports.

Run `docker compose up --build -d`. Alembic runs before API startup.
Open http://localhost:8080. For tablets on a LAN, use an approved HTTPS reverse proxy
and configure the port binding deliberately; default is loopback-only.
Service workers require HTTPS except on localhost.

## Provision

Generate tenant/factory UUIDs. Provision distinct operator, supervisor, admin and device accounts:

```sh
docker compose exec -e PROVISION_TOKEN api python -m app.provision --tenant <uuid> --factory <uuid> --role admin
```

Export PROVISION_TOKEN in the operator shell beforehand; never paste secrets into source, logs or issues.
The CLI prints only the identity UUID. Use the token on the tablet login screen.
Admin creates equipment via POST /equipment; /api/docs exposes the API from the tablet origin.
Register sensors via POST /sensors with the equipment UUID and provisioned device identity UUID.
Credentials are scoped to exactly one tenant/factory; provision multiple identities for multi-factory staff.
Revocation: privileged operator sets identities.active=false for the specific identity.
Token rotation requires a new randomly generated token/hash. No public signup or default credentials.

## Edge

`pip install -r edge/requirements.txt`. Configure DEVICE_TOKEN and INGEST_URL
(https://your-host/api/readings), then run:

```sh
python edge/gateway.py --sensor <uuid> --transport simulator --once
python edge/gateway.py --sensor <uuid> --transport tcp --host <meter-ip> --address <input-register> --scale <scale>
python edge/gateway.py --sensor <uuid> --transport rtu --serial-port /dev/ttyUSB0 --address <register>
```

The adapter only reads one unsigned input register. Confirm manufacturer register map,
unit, scale, word order, serial parity and calibration before extending to real meters.
It is not ESP32 firmware. Outbox SQLite persists across restarts; permanent HTTP failures
are quarantined in the error column for operator review. Network failures retain the event.
Use a protected filesystem, monitor disk space and quarantine size. No relay/PLC writes.
The reference sampler collects kW, not energy. Reports require externally calculated
energy_kwh_interval deltas with interval_seconds; cumulative counters must not be summed.

## Automatic reports and evidence

Enable `docker compose --profile automation up -d reports` after setting REPORT_TOKEN.
The worker retries previous day and previous month hourly (Asia/Seoul). Unique keys prevent duplicates.
Snapshots freeze data at first generation; late arrivals require a future explicit revision workflow,
not silent overwriting. Backfill missing days by calling POST /reports per date.
XLSX includes source IDs; PDF is a compact English numeric summary. Korean UI labels remain in the tablet.
One selected meter avoids double-counting main and sub-meters. Bad data is excluded;
simulator and boundary prorations are estimates. Missing coverage is reported, not extrapolated.
Production-ratio energy assessment is an estimate only; weather, operating hours and mix need a validated model.

## Backup and restore rehearsal

```sh
docker compose exec -T db pg_dump -U factory -d factory -Fc > factory.dump
docker compose exec -T db createdb -U factory factory_restore_check
docker compose exec -T db pg_restore -U factory -d factory_restore_check < factory.dump
```

Restore into a separate test database, compare row counts and tenant access, then test application restart.
Encrypt backups, restrict access, set retention and rehearse restoration before field use.
This Compose setup uses a database owner for local pilot convenience. Before production, split migration
and application DB roles; deny DDL, audit UPDATE/DELETE/TRUNCATE, restrict DB network and enforce TLS,
rotate tokens, add rate limits, session expiry/SSO, monitoring and retention.
Application queries enforce tenant+factory scope and composite foreign keys reject cross-scope references.
Offline records reside in IndexedDB on the physical device; use managed tablets and OS access control.
Logout clears displayed/session data, but preserves partitioned unsent records for the original user.

## Verification

```sh
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m unittest discover -s tests -v
```

From repository root: `python -m unittest discover -s edge -v`, `npm --prefix frontend test`.
Browser test: install Playwright/Chromium and run `python frontend/tests/browser_test.py`.
CI runs PostgreSQL migration, API isolation/approval/ingestion/export tests, edge, queue and Chromium.
Local restricted shell cannot open sockets, install DB dependencies or access Docker; CI supplies these.

## Remaining acceptance gates

Site forms, photo/voice uploads, QR, real Modbus/ESP32 commissioning, semantic embeddings and model evaluation,
weather-adjusted energy baseline, carbon factors/LOT allocation and passport approval remain later work.
DeepSeek Harness is not installed or integrated. Pin and review it in an isolated developer preview.
No production deployment, industrial control or certified performance is implied by software tests.
