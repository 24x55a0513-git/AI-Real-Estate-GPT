# Repair report

Scope: the uploaded `real-estate-gpt.zip` was inspected, repaired in a separate copy, and repackaged. The original ZIP was not modified.

## Environment limits (important)
The repair sandbox had **no internet, no MySQL, no browser, and none of the Python/npm dependencies installed**. So the backend could not be started, pytest could not run, and `tsc`/`vite build`/Vitest could not run. Everything below is labelled by what was actually executed.

## 1. Audit of the original project
The code base was already well structured (routers → services → repositories, Alembic migration, tests, all UI pages present, every frontend API call has a matching backend route). Problems found by reading the code:

| # | Problem | Evidence |
|---|---|---|
| 1 | **CORS allow-list contained only port 5173.** Vite silently moves to 5174 when 5173 is busy; that origin was rejected. | `CORS_ORIGINS` default and `.env.example` listed only 5173 |
| 2 | **Unhandled errors (500) carried no CORS headers.** Starlette answers them outside the CORS middleware, so a stopped MySQL or missing tables on `/api/properties` and `/api/properties/facets` shows up in the browser as "No Access-Control-Allow-Origin" and hides the real error. | `@app.exception_handler(Exception)` registered; no DB-specific handling |
| 3 | `/api/health` swallowed the exception, logged nothing, and did not check tables. | `health.py` |
| 4 | **`requirements.txt` pins cannot install on Python 3.14** (pydantic 2.10 → pydantic-core without 3.14 wheels; SQLAlchemy 2.0.36 predates 3.14 support; `uvicorn[standard]` native extras). The user has Python 3.14. | pins vs. published wheel support |
| 5 | `.env` was looked up relative to the current directory; a missing/invalid setting produced a raw pydantic traceback; `CHANGE_ME` placeholders and `mysql://` URLs were not caught. | `config.py` |
| 6 | Frontend: blank `VITE_API_URL=` made the base `"/api"` (requests hit the Vite server); a value ending in `/api` produced `/api/api`. | `api.ts` |
| 7 | Frontend: `@types/node` missing although `vite.config.ts` uses `node:path`/`__dirname` (typecheck would likely fail); `tsc -b --noEmit` is version-sensitive. | `package.json`, `vite.config.ts` |
| 8 | Test tools mixed into runtime requirements; no lockfiles. | `requirements.txt`, no `package-lock.json` |
| 9 | Seed: demo user/admin passwords hard-coded in source and README; seeding skipped everything when any demo row existed (not incremental). | `seed.py` |
| 10 | `.env.example` suggested putting `ADMIN_*` variables in `.env`, which the scripts never read. | `.env.example` vs `create_admin.py` |
| 11 | No clean seam for an optional AI parser or a licensed data provider. | `chat_service.py` called the parser directly |

Not found: committed real secrets (only placeholders), plaintext passwords, missing files, broken imports, authorization holes.

## 2. Changes (UI untouched)
No component, page, style, layout or route under `frontend/src` was changed except `services/api.ts`.

Backend: `core/config.py` (absolute `.env` path, friendly startup errors, URL validation, CORS regex = any localhost port in development only, refuses `.*` in production); `main.py` (catch-all inside the CORS layer, 503 handler for database errors, startup DB check); `db/errors.py` (new, safe MySQL error hints); `routes/health.py` (real connect + table check, 503 with hint); `requirements.txt`/`requirements-dev.txt`; `.env.example`; `scripts/seed.py` (incremental, no hard-coded passwords, development only); `scripts/check_db.py` (new); `services/query_understanding.py` (new optional-AI seam with fallback) wired into `chat_service.py`; `services/property_feed.py` (new, unused by the app); new tests `test_cors_and_health.py`, `test_config.py`, `test_seed.py`, `test_query_understanding.py`, `test_property_feed.py`.

Frontend: `services/api.ts` (`resolveApiBase`, actionable error text), `package.json` (`@types/node`, `tsc --noEmit`, engines), `tsconfig.json`, `vite.config.ts` (comment only), `.env.example`, new `api.test.ts`.

Docs: README rewritten, this report added.

## 3. Verification actually performed in the sandbox
| Check | Result |
|---|---|
| Parser tests (`tests/test_nlp_parser.py`, 31 cases) with a minimal pytest stand-in | **Executed: 31 passed** |
| Optional-AI fallback tests (`test_query_understanding.py`, 4 cases) | **Executed: 4 passed** |
| Byte-compile of all 57 backend Python files; first-party import names resolve | **Executed: passed** |
| SQLAlchemy models vs Alembic migration (tables and columns, static comparison) | **Executed: identical** |
| Frontend syntax parse of all 37 TS/TSX files (syntax only, not a type check) | **Executed: 0 errors** |
| Frontend utility logic (price formatting, `toNumber`, `resolveApiBase`) run in Node | **Executed: 12 assertions passed** |
| Every frontend API call has a backend route (static regex comparison) | **Executed: 28/28 matched** |
| Seed data vs the four example prompts, simulated in plain Python | **Executed: results as expected** (2BHK Hyderabad <60L → 1; rentals <25k → 3; villas 80L–1.5Cr → 2) |

## 4. Acceptance checklist
| Item | Status |
|---|---|
| Backend starts | NOT TESTED |
| Frontend starts | NOT TESTED |
| MySQL connects | NOT TESTED |
| Migrations run | NOT TESTED (static model/migration match passed) |
| Seed loads | NOT TESTED (script syntax and data checked; incremental logic covered by an unrun test) |
| Health endpoint | NOT TESTED (tests written) |
| Swagger opens | NOT TESTED |
| Frontend API URL correct | PASSED (logic executed) |
| CORS for actual dev origin | NOT TESTED (fix and tests written; reasoning from Starlette's documented middleware order) |
| Listings, search, filters, details, comparison, favorites, auth, inquiries | NOT TESTED (existing and new tests not run) |
| Assistant parsing | PASSED (31 executed) |
| Assistant returns database-backed results | NOT TESTED (test written; plain-Python simulation passed) |
| Navigation / buttons | NOT TESTED in a browser (static review: all routes map to existing pages) |
| Frontend `tsc` / production build / Vitest | NOT TESTED |
| Setup instructions match files | Reviewed by hand against the delivered tree; not executed on Windows |

## 5. What to run first on your machine
1. `pip install -r requirements-dev.txt` then `pytest -q` in `backend\`.
2. `npm install`, `npm run typecheck`, `npm test`, `npm run build` in `frontend\`.
3. Setup steps 3.2–3.6 in the README, then `/api/health`.
Send back any failure output; a first run can reveal small issues that could not be seen offline.

## 6. Which CORS cause did you hit?
Cause 1 is certain for any request from `http://localhost:5174`. Cause 2 produces the identical browser message when MySQL is down or tables are missing. After the fix, `/api/health` tells them apart: `ok` means CORS/config; anything else carries the exact database hint.
