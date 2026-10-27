# Real Estate GPT

An AI-assisted real-estate discovery platform: search and filter properties, chat with a natural-language assistant, compare listings, save favorites, send inquiries, and manage listings from an admin dashboard.

> **All listings are fictional demonstration data.** The assistant uses **rule-based natural-language parsing in Python, not a large language model**, and works with no paid AI service. Nothing in this project is deployed; it has been prepared to run locally and to be deployed later.

**Read first:** [`docs/REPAIR_REPORT.md`](docs/REPAIR_REPORT.md) lists what was wrong, what was changed, and exactly which checks were and were **not** executed (the repair environment had no MySQL, no internet and no package installation).

---

## 1. What is in the box

| Part | Technology |
|---|---|
| Frontend (`frontend/`) | React 18, TypeScript, Vite, Tailwind CSS 3, React Router 6, TanStack Query 5, React Hook Form, Zod |
| Backend (`backend/`) | Python, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PyMySQL, bcrypt, PyJWT |
| Database | MySQL 8 (utf8mb4) |
| Tests | Pytest (backend), Vitest (frontend) |

```
real-estate-gpt/
├── README.md  render.yaml  .gitignore
├── docs/REPAIR_REPORT.md
├── backend/
│   ├── app/{api/routes, core, db, models, schemas, repositories, services, main.py}
│   ├── alembic/versions/0001_initial_schema.py   alembic.ini
│   ├── scripts/{seed.py, create_admin.py, check_db.py}
│   ├── tests/   requirements.txt   requirements-dev.txt   .env.example
└── frontend/
    ├── src/{components, pages, layouts, hooks, services, types, utils, routes, test}
    └── package.json  vite.config.ts  tailwind.config.js  vercel.json  .env.example
```

### Architecture
```
Browser (React SPA) --JSON + Bearer JWT--> FastAPI --SQLAlchemy--> MySQL
   routes (api/) -> services (rules) -> repositories (all SQL)
   assistant: message -> QueryParser (rule-based) -> SearchCriteria -> PropertyRepository.search -> explained results
```
* `services/nlp_parser.py` is dependency-free and never touches the database. `services/query_understanding.py` is the seam where an **optional** AI parser can be plugged in later (see section 9); with no credentials configured, nothing changes.
* `services/property_feed.py` is the boundary for a **future licensed property-data provider**: an adapter yields validated `PropertyCreate` records and `import_feed` stores them in MySQL (see section 10). Nothing in the running app calls it.

---

## 2. Required software

| Software | Version | Notes |
|---|---|---|
| Windows | 10 or 11 | PowerShell 5.1 or 7 |
| Python | **3.12 or 3.13 recommended**; 3.14 should work with the pinned minimums but was **not tested** | Older dependency pins had no Python 3.14 wheels, which is why `requirements.txt` now sets newer minimum versions. See Troubleshooting if `pip install` fails on 3.14. |
| Node.js | 20 or 22 LTS (22 recommended) | includes npm |
| MySQL | 8.x | MySQL Installer "Server only" is enough |
| VS Code (or any editor) | any | optional |

Check what you have (each command is read-only):
```powershell
py -0p            # lists every installed Python and its path
python --version
node --version
npm --version
mysql --version   # if "not recognized", see Troubleshooting
```

---

## 3. First-time setup on Windows (PowerShell)

Every block says which folder to run it in. Run the blocks in order.

### 3.1 Extract and open the project  (run anywhere)
```powershell
# Adjust the zip path if your download went elsewhere.
New-Item -ItemType Directory -Force "$HOME\Projects" | Out-Null
Expand-Archive -Path "$HOME\Downloads\real-estate-gpt-fixed.zip" -DestinationPath "$HOME\Projects" -Force
cd "$HOME\Projects\real-estate-gpt"
code .            # VS Code. Other editors: just open this folder.
```

### 3.2 Create the MySQL database and a dedicated user  (run anywhere)
```powershell
mysql -u root -p
```
If PowerShell says `mysql` is not recognized, call it by full path instead:
`& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p`

At the `mysql>` prompt (choose your own strong password and remember it for step 3.3):
```sql
CREATE DATABASE IF NOT EXISTS real_estate_gpt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'realestate_user'@'localhost' IDENTIFIED BY 'ChangeThisStrongPassword1';
GRANT ALL PRIVILEGES ON real_estate_gpt.* TO 'realestate_user'@'localhost';
-- optional, only for running the test-suite against MySQL (name must contain "test"):
CREATE DATABASE IF NOT EXISTS real_estate_gpt_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON real_estate_gpt_test.* TO 'realestate_user'@'localhost';
EXIT;
```
`CREATE ... IF NOT EXISTS` is safe to re-run: it never drops or empties anything. If the MySQL service is not running: `Get-Service MySQL*` then `Start-Service MySQL80` (as Administrator), or start it from `services.msc`.

### 3.3 Backend setup  (run in `real-estate-gpt\backend`)
```powershell
cd "$HOME\Projects\real-estate-gpt\backend"

# Create the virtual environment. Use a Python you verified with `py -0p`:
py -3.12 -m venv .venv          # or: py -3.13 -m venv .venv   (or: python -m venv .venv for whatever is default)
.\.venv\Scripts\Activate.ps1    # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python --version                # confirm the version inside the venv
python -m pip install --upgrade pip
pip install -r requirements-dev.txt     # runtime + test tools (use requirements.txt for runtime only)

# Create backend\.env from the template and put a random secret into it
Copy-Item .env.example .env
$secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
(Get-Content .env) -replace '^SECRET_KEY=.*', "SECRET_KEY=$secret" | Set-Content .env -Encoding ascii
notepad .env     # replace CHANGE_ME in DATABASE_URL with the MySQL password from step 3.2, then save
```
In `DATABASE_URL`, URL-encode special characters in the password (`@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`, `?` → `%3F`, `%` → `%25`). The app refuses to start while the `CHANGE_ME` placeholder is still in `DATABASE_URL` and prints which setting is wrong.

```powershell
# Still in backend\ with the venv active:
python -m scripts.check_db        # expect: Connection ok. Schema will say "missing" until the next command.
alembic upgrade head              # creates all tables (safe to re-run; it never deletes data)
python -m scripts.check_db        # expect: "OK - the database is reachable and the schema is in place."
python -m scripts.seed            # 25 fictional demo listings; safe to re-run (no duplicates)
```
Optional **development-only** demo accounts (a random password is generated and printed once, or set `$env:DEMO_USER_PASSWORD` / `$env:DEMO_ADMIN_PASSWORD` first):
```powershell
python -m scripts.seed --with-demo-users
```
Create your own administrator instead (prompts for e-mail and password; nothing is hard-coded):
```powershell
python -m scripts.create_admin
# or turn an existing registered user into an admin:
python -m scripts.create_admin --promote
```

### 3.4 Start the backend  (run in `real-estate-gpt\backend`, venv active)
```powershell
uvicorn app.main:app --reload --port 8000
```
The startup log prints `Database OK (all tables present, migration 0001)` or an explicit `Database NOT ready: ...` message with the fix.

### 3.5 Check the backend  (open a second PowerShell window; any folder)
```powershell
Invoke-RestMethod http://localhost:8000/api/health        # expect status=ok, database=ok, schema=ok
Start-Process http://localhost:8000/docs                   # Swagger UI
(Invoke-RestMethod "http://localhost:8000/api/properties?page_size=3").total   # number of properties in MySQL
# CORS check for a Vite fallback port (look for access-control-allow-origin: http://localhost:5174):
curl.exe -i -H "Origin: http://localhost:5174" http://localhost:8000/api/properties/facets
```
`/api/health` really connects to MySQL and checks that every table exists. It answers **HTTP 503** with a `detail` hint (for example "Cannot connect to MySQL…" or "run alembic upgrade head") when something is wrong, so a running Uvicorn is never mistaken for a working database.

### 3.6 Frontend setup and start  (in that same second window, in `real-estate-gpt\frontend`)
```powershell
cd "$HOME\Projects\real-estate-gpt\frontend"
npm install
Copy-Item .env.example .env       # VITE_API_URL=http://localhost:8000  (no /api, no trailing slash)
npm run dev
```
Open the address Vite prints (normally **http://localhost:5173**; if that port is busy Vite uses 5174, 5175 … and that works too). Restart `npm run dev` after editing `frontend\.env`.

### 3.7 Try the features
1. **Home** → search *Buy / Hyderabad*, or open **Explore** and use filters; refresh and the filters stay (they live in the URL).
2. **AI Assistant** → *Find a 2BHK apartment in Hyderabad under ₹60 lakh with parking*, then *Compare the cheapest matching properties*.
3. Register / log in → heart a property → *Add to compare* on 2–4 cards → *Contact About This Property*.
4. Log in as an admin → **Admin** → add/edit a property, change status, review inquiries.

---

## 4. Daily startup checklist

Window 1 (backend):
```powershell
cd "$HOME\Projects\real-estate-gpt\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
Window 2 (frontend):
```powershell
cd "$HOME\Projects\real-estate-gpt\frontend"
npm run dev
```
Then: MySQL service running → http://localhost:8000/api/health shows `ok` → open the Vite address. After pulling new code: `pip install -r requirements-dev.txt`, `alembic upgrade head` (backend) and `npm install` (frontend).

---

## 5. Configuration reference

**`backend/.env`** (create from `.env.example`; never commit it)

| Variable | Required | Meaning |
|---|---|---|
| `ENVIRONMENT` | no (default `development`) | `production` enforces a strong `SECRET_KEY` and disables the "any localhost port" CORS rule |
| `DATABASE_URL` | **yes** | `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4` |
| `SECRET_KEY` | **yes** | random string, 32+ characters in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no (60) | login token lifetime |
| `CORS_ORIGINS` | no | comma-separated exact origins, no trailing slash. Defaults to `http://localhost:5173,http://127.0.0.1:5173` |
| `CORS_ORIGIN_REGEX` | no | extra allowed origins as a regex (e.g. Vercel preview URLs). Blank = none. `.*` is refused in production |

Helper scripts read a few **process** environment variables (not `.env`): `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`, `DEMO_USER_PASSWORD`, `DEMO_ADMIN_PASSWORD`, `TEST_DATABASE_URL`. Set them for one PowerShell session, e.g. `$env:ADMIN_EMAIL = "you@example.com"`.

**`frontend/.env`**: `VITE_API_URL` only (default `http://localhost:8000`). The app appends `/api` exactly once; a trailing `/api` or `/` in the value is tolerated. Only `VITE_*` variables reach the browser, so never put secrets there.

Missing or invalid settings stop the backend at startup with a list such as `- SECRET_KEY: is missing` and the exact path where `.env` is expected (`backend\.env`, resolved from the code location, so the working directory no longer matters).

**CORS in one paragraph.** In development the backend accepts the origins in `CORS_ORIGINS` **and** any `http(s)://localhost|127.0.0.1|[::1]:<port>`, so Vite's automatic port change can no longer break the app. In production only `CORS_ORIGINS` (plus an explicit `CORS_ORIGIN_REGEX`, if you set one) is accepted; there is no `*`. CORS headers are also present on 4xx, database-outage (503) and unexpected-error (500) responses, so the browser shows the real error instead of a misleading CORS message.

---

## 6. Testing

```powershell
# Backend: in backend\, venv active. Default run uses an in-memory SQLite database and never touches your MySQL data.
pytest -q

# Optional: run the same tests against a throw-away MySQL schema (database name must contain "test")
$env:TEST_DATABASE_URL = "mysql+pymysql://realestate_user:PASSWORD@localhost:3306/real_estate_gpt_test?charset=utf8mb4"
pytest -q
Remove-Item Env:TEST_DATABASE_URL

# Frontend: in frontend\
npm run typecheck
npm test
npm run build
```
The suite covers authentication, authorization (users cannot see each other's favorites, inquiries or chats; admin routes), search filters and pagination, comparison, favorites, inquiries, the language parser, the assistant on top of the seeded data (database-backed answers, honest "no match" and unknown-city replies), CORS (including preflight, other localhost ports, foreign origins, error responses), the health endpoint (OK / database down / missing tables), settings validation, seed repeatability and the optional-AI fallback.

---

## 7. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Browser: *"No 'Access-Control-Allow-Origin' header"* | Open `http://localhost:8000/api/health`. If it is not `ok`, the real problem is the database (see the hint in the response); fix that. If it **is** `ok`, check that `frontend\.env` has `VITE_API_URL=http://localhost:8000`, restart `npm run dev`, and confirm the address bar origin with the `curl.exe -i -H "Origin: ..."` command from 3.5. |
| UI banner *"Cannot reach the API at …"* | Backend not running, wrong `VITE_API_URL`, or wrong port. The message names the exact URL the frontend is using. |
| `pip install` fails with *pydantic-core*, *PyO3*, *Rust*, *cargo* or a long build error | You are on a Python version without wheels for the pinned packages (typically 3.14 with old pins). Run `pip install --upgrade pip` and retry. If it still fails, install Python 3.12 next to 3.14 (`winget install Python.Python.3.12`) and recreate the venv with `py -3.12 -m venv .venv` after `Remove-Item -Recurse -Force .venv`. |
| Backend exits with *"invalid or missing configuration"* | Read the listed variable names. `.env` must be `backend\.env`. Replace every `CHANGE_ME`. |
| `Access denied for user` | Wrong user/password in `DATABASE_URL`; URL-encode special characters. |
| `Unknown database 'real_estate_gpt'` | Run step 3.2. |
| `Can't connect to MySQL server` | MySQL service not running (`Start-Service MySQL80`) or wrong host/port. |
| Health says *schema missing* / *Table doesn't exist* | Run `alembic upgrade head` in `backend\`. |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'app'` | You are not in `backend\`. `cd` there; run Python commands with the venv active. |
| `Port 8000 is already in use` | `Get-NetTCPConnection -LocalPort 8000 \| Select OwningProcess`, then `Stop-Process -Id <pid>`; or use `--port 8001` and set `VITE_API_URL=http://localhost:8001`. |
| Vite opened on 5174 | Fine in development; nothing to change. Close the old Vite window if you want 5173 back. |
| Pages load but no properties | Run `python -m scripts.seed` and check `http://localhost:8000/api/properties`. |
| Login says incorrect e-mail or password for demo users | Passwords are random per seed run. Create an account on the Register page, or run `python -m scripts.create_admin`. |

---

## 8. Deployment guide (not performed; prepared only)

Deploying needs external accounts and may involve costs or usage limits that change over time. **Check each provider's current pricing and free-tier terms; free tiers are not guaranteed and instances may sleep.**

**Order:** database → backend → frontend → put the frontend URL into the backend's CORS setting → verify.

1. **Managed MySQL 8 database** (any provider that offers MySQL-compatible hosting). Create a database and a user; if the provider requires TLS add its parameters to the URL. Final form: `mysql+pymysql://USER:PASSWORD@HOST:PORT/DBNAME?charset=utf8mb4` (URL-encode special characters). Restrict network access if the provider allows it.
2. **Backend** (example: Render via `render.yaml`, or any host that runs Python)
   * Root directory `backend`; build `pip install -r requirements.txt`
   * Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`  (migrations run on every start; they are idempotent)
   * Health check path: `/api/health` (returns 503 until MySQL is reachable and migrated)
   * Environment variables (set in the host's dashboard, never in Git): `ENVIRONMENT=production`, `SECRET_KEY` (random, 32+), `DATABASE_URL`, `CORS_ORIGINS=https://<your-frontend-domain>` (exact origin, no trailing slash), optional `CORS_ORIGIN_REGEX` for preview URLs, optional `ACCESS_TOKEN_EXPIRE_MINUTES`
   * One-time data: create the admin with `python -m scripts.create_admin` (host shell, or locally with `DATABASE_URL` pointed at the managed DB). `python -m scripts.seed` loads the **fictional demo** listings; skip it for a site meant to show only real data. `--with-demo-users` is refused unless `ENVIRONMENT=development`.
   * `/docs` stays reachable in production; restrict it at the host if you do not want it public.
3. **Frontend** (example: Vercel, Netlify or any static host)
   * Root directory `frontend`; install `npm install` (or `npm ci` once `package-lock.json` is committed); build `npm run build`; output `dist`; `vercel.json` already rewrites all routes to `index.html`
   * Environment variable at build time: `VITE_API_URL=https://<your-backend-domain>` (no `/api`)
4. Update the backend's `CORS_ORIGINS` with the final frontend URL and redeploy the backend.
5. **Verify:** `https://<backend>/api/health` shows `ok`; open the site; Explore loads; register; save a favorite; ask the assistant; submit an inquiry; log in as admin. Check the browser console for CORS errors.
6. **Secrets:** keep them in the host's secret store; rotate `SECRET_KEY` (this logs everyone out) and the database password if they were ever exposed. Do not claim "production-ready" until you have also added the items under Known limitations (rate limiting, e-mail delivery, backups, monitoring).

---

## 9. The assistant, and adding an optional AI model later

* Supported today: city, locality, buy/rent, property type, bedrooms (exact, "at least", "3+"), bathrooms, price (lakh, crore, thousand, "per month", ranges, "around"), area, furnishing, parking, amenities, "cheapest", "compare". Examples that work: *Find a 2BHK apartment in Hyderabad under ₹60 lakh*, *Show rental flats below ₹25,000 per month*, *Find villas between ₹80 lakh and ₹1.5 crore*, *Show properties with parking and at least two bedrooms*.
* Every result comes from a database query; the "why this matches" reasons are computed from the stored values. When nothing matches the assistant says so and offers relaxations whose result counts come from the database. For a city with no listings it says so instead of inventing any. The API reports `parser: "rule-based"`; it never claims to be an LLM.
* **Adding an AI parser later:** implement `QueryParser` (a `name` and `parse(message, known_localities) -> ParsedQuery`) in a new module, and return it from `configured_primary_parser()` in `backend/app/services/query_understanding.py` only when its API key is present in the environment. The model must only output structured criteria. If it is absent or raises, the rule-based parser answers, so the website and core search never depend on it. No AI provider is installed or configured today.

## 10. Connecting real property data later

The website and assistant read only from MySQL. To bring in real listings from a **licensed** source, write an adapter implementing `PropertyFeed` in `backend/app/services/property_feed.py` (map the provider's fields to `PropertyCreate`), then run `import_feed(db, adapter)` from a script or scheduled job. Imports are repeatable (existing title+city+locality are skipped), real records are stored with `is_demo=false`, and demo rows (`is_demo=true`) stay separate. Confirm the provider's terms permit displaying their data and photos before publishing.

---

## 11. Security notes

* bcrypt password hashing; generic "incorrect e-mail or password" with constant-time-ish verification for unknown users; passwords never logged.
* JWT with expiry; the role is read from the database on every request, never from the token. Registration can never create an admin. Users can only read or modify their own favorites, inquiries and chats (another user's chat id returns 404).
* Pydantic validation on all input, parameterised SQL with escaped LIKE wildcards, explicit CORS allow-list (no `*`), security headers, generic 500 bodies with details only in server logs, database errors reported as short hints without credentials or SQL.
* No real credentials are in this repository: `.env` files are git-ignored, only `.env.example` templates with placeholders ship. Demo-user passwords are no longer in source code.
* **Token storage trade-off:** the JWT is kept in `localStorage` (survives refresh, works across separate frontend/backend domains). An XSS bug could read it; the app avoids `dangerouslySetInnerHTML` and tokens expire. A hardened alternative is httpOnly cookies plus CSRF protection.

## 12. Known limitations

* **Checks that have not been executed anywhere yet:** the backend test-suite, Alembic against MySQL, the seed script, FastAPI start-up, `tsc`, `vite build` and Vitest (see `docs/REPAIR_REPORT.md`). Run section 6 on your machine; any failure output is useful.
* No `package-lock.json` or pinned Python lock file is included (they can only be generated by a real install). After a successful install run `npm install` (creates `package-lock.json`) and `pip freeze > requirements.lock.txt`, and commit both.
* Python 3.14 compatibility of the dependency set is untested; 3.12/3.13 are recommended.
* Assistant is rule-based: common English phrasings only, no typo tolerance, no LLM.
* Property photos are Unsplash URLs that were not verified; the UI shows a placeholder if one fails to load. Check Unsplash's licence/attribution terms before a public launch.
* Inquiries are stored only; no e-mail is sent. No password reset or e-mail verification. No rate limiting or login lockout. Tokens cannot be revoked before expiry. No image upload (URLs only).
* Comparison shows listed data only; it is not valuation or investment advice.
* If you ever seeded with the old `--with-demo-users`, those two accounts exist with publicly known passwords. Remove them before sharing the database: `DELETE FROM users WHERE email IN ('demo.user@example.com','demo.admin@example.com');`

## 13. API endpoints (all under `/api`; full docs at `/docs`)

| Area | Endpoints |
|---|---|
| Health | `GET /health` |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| Profile | `PATCH /users/me`, `POST /users/me/password`, `GET /users/me/summary` |
| Properties | `GET /properties`, `GET /properties/facets`, `GET /properties/compare?ids=1,2`, `GET /properties/{id}` |
| Favorites | `GET /favorites`, `GET /favorites/ids`, `PUT /favorites/{id}`, `DELETE /favorites/{id}` |
| Inquiries | `POST /inquiries`, `GET /inquiries/mine` |
| Assistant | `POST /chat/message`, `GET /chat/sessions`, `GET/DELETE /chat/sessions/{id}` |
| Admin | `GET /admin/stats`, `GET/POST /admin/properties`, `GET/PUT/DELETE /admin/properties/{id}`, `PATCH /admin/properties/{id}/status`, `GET /admin/inquiries`, `PATCH /admin/inquiries/{id}` |

## 14. Database schema
`users` · `properties` (price `DECIMAL(14,2)`, CHECK constraints, composite search index) · `property_amenities` · `property_images` · `favorites` (unique user+property) · `inquiries` (user/property `ON DELETE SET NULL`) · `chat_sessions` · `chat_messages`. Money is INR; for rent listings `price` is the **monthly rent**. Normal start-up never deletes data; `scripts.seed --reset` removes only rows flagged `is_demo`.

---
## Portfolio material
**Description:** Real Estate GPT is a full-stack property discovery app (React, TypeScript, FastAPI, MySQL) featuring a transparent rule-based conversational search assistant that converts plain-English requests - including Indian lakh/crore budgets - into SQL-backed searches, with comparison, favorites, inquiries, JWT auth and a role-protected admin dashboard.

**Resume bullets (truthful as built; adjust after you run/deploy it):**
- Built a full-stack real-estate platform with React/TypeScript and FastAPI/SQLAlchemy on a normalised MySQL schema (7 tables, FK/CHECK/unique constraints, Alembic migration).
- Designed a dependency-free rule-based NLP parser that extracts city, type, bedrooms, area and Indian-currency budgets (lakh/crore/thousand) into Pydantic criteria that drive database queries and explain each match.
- Implemented bcrypt/JWT authentication with server-enforced RBAC, per-user data isolation, and an automated pytest suite covering auth, search filters, favorites, inquiries, admin permissions and the assistant.

**Two-minute explanation:** "Real Estate GPT lets people search properties in plain English. A user types something like '2BHK in Hyderabad under 60 lakh with parking'. My Python parser normalises the text, extracts city, type, bedrooms, buy-vs-rent and the budget - handling lakh and crore and refusing to confuse a monthly rent with a sale price - and produces a Pydantic criteria object. A separate search service turns that into a parameterised SQLAlchemy query against MySQL and returns real records, each with reasons it matched; if nothing matches it suggests relaxations, with counts computed from the database. I chose rules over an LLM deliberately: it's deterministic, free, testable and never hallucinates listings, and the criteria interface lets me plug in an LLM later. Around that, there's JWT auth with server-side role checks, favorites and inquiries in MySQL, a comparison engine, and an admin dashboard. The React frontend uses TanStack Query for caching and keeps filters in the URL."

**Interview Q&A**
- *Why rules instead of an LLM?* Deterministic, testable, free, no hallucinated listings; the parser sits behind a criteria interface so an LLM can be added later.
- *How do you prevent confusing rent and price?* Explicit buy/rent words win; otherwise an amount below ₹1 lakh is assumed to be rent and the assumption is shown; contradictory combinations raise a warning.
- *How is authorization enforced?* A FastAPI dependency loads the user from the DB and checks the role on every admin route; the UI hiding is cosmetic only.
- *Why Decimal for money?* Avoid binary floating-point error; the DB column is `DECIMAL(14,2)` and only serialised to a number at the API boundary.
- *How do you avoid SQL injection?* SQLAlchemy bound parameters, validated Pydantic inputs, escaped LIKE wildcards.
- *What would you improve?* Rate limiting, httpOnly cookies, e-mail delivery, an LLM parser, CI, broader frontend tests.

**Technologies demonstrated:** React, TypeScript, Vite, Tailwind, React Router, TanStack Query, React Hook Form, Zod, FastAPI, Pydantic, SQLAlchemy 2, Alembic, MySQL, JWT, bcrypt, Pytest, Vitest, REST/OpenAPI, RBAC, NLP-style text parsing, Git/GitHub, Vercel/Render deployment.

## Credits
Demo photos are Unsplash images (Unsplash License). All property data is fictional.
