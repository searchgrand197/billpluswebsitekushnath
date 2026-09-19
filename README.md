# Merged Kushnath project (Live ecommerce + Billvice POS)

## Run locally

```bash
# from repo root (folder that contains manage.py)
.\.venv\Scripts\activate
python manage.py runserver
```

| App | URL |
|-----|-----|
| Storefront | http://127.0.0.1:8000/ |
| Billvice POS | http://127.0.0.1:8000/billvice/ |
| Billvice login | http://127.0.0.1:8000/billvice/login |
| Admin | http://127.0.0.1:8000/admin/ |

Optional print microservice: `python print_service.py` → POST `/print`, GET `/health`

---

## How frontend is handled (important for deploy)

Two different frontends — do not mix them:

| What | Folder | Served by | URL prefix |
|------|--------|-----------|------------|
| **Billvice POS** (React/Vite) | `frontend/dist/` | `kushnath.billvice_views.serve_billvice` | `/billvice/` |
| **Live storefront** (legacy build) | `build/` | `kushnath_dashboard.views.serve_frontend` | assets / catch-all |

### Billvice request flow

```
Browser  →  /billvice/login
Django   →  serve_billvice(path="login")
         →  no file named "login" in dist
         →  returns frontend/dist/index.html   ← always this file, never build/index.html
Browser  →  loads /billvice/assets/*.js
React    →  Router basename="/billvice" → <Login />
```

### Build Billvice before deploy

```bash
cd frontend
npm install
npm run build
```

Must produce:

```
frontend/dist/index.html          # asset URLs start with /billvice/
frontend/dist/assets/index-*.js
frontend/dist/assets/index-*.css
```

Config that must stay in sync:

- `frontend/vite.config.js` → `base: '/billvice/'`
- `frontend/src/main.jsx` → `<BrowserRouter basename="/billvice">`
- `kushnath/settings.py` → `BILLVICE_DIST_DIR = BASE_DIR / "frontend" / "dist"`

If `frontend/dist/index.html` is missing, `/billvice/` returns **503** with build instructions (not a blank page).

---

## Production checklist

1. On CI or your machine: `cd frontend && npm ci && npm run build`
2. Upload code **including** `frontend/dist/`
3. Confirm on server: `ls frontend/dist/index.html`
4. Point nginx at Django for `/billvice/` — see `deploy/nginx.example.conf`
5. Optional: nginx `alias` for `/billvice/assets/` to `frontend/dist/assets/`
6. Set env on server:
   ```bash
   export DJANGO_DEBUG=false
   export DJANGO_SECRET_KEY='long-random-string'
   # optional: keep DB outside deploy folder so uploads never wipe data
   export DJANGO_DB_PATH=/var/data/kushnath/db.sqlite3
   ```
7. Restart gunicorn/daphne after uploading a new `dist/`

### Critical: do not wipe data on deploy

All Billvice products/invoices live in **`db.sqlite3`** (and uploads in **`media/`**).

When you re-upload the project zip/folder:

- **Do not overwrite** `db.sqlite3` or `media/` on the server
- Or set `DJANGO_DB_PATH` to a path outside the app folder

If you replace `db.sqlite3`, the app “works” but looks empty and sessions reset (page jumps back to login).

### Page disappears after some time

Usually the session cookie was dropped (HTTPS proxy) or the DB was replaced. Fixes above:

- `SECURE_PROXY_SSL_HEADER` + secure cookies when `DJANGO_DEBUG=false`
- `SESSION_SAVE_EVERY_REQUEST = True`
- nginx must send `X-Forwarded-Proto $scheme` (see example conf)

### Common deploy mistakes

| Symptom | Cause |
|---------|--------|
| Blank `/billvice/` page | Old/wrong `index.html` (from `build/`) or assets 404 |
| `/billvice/login` 404 from nginx | nginx serving static SPA without fallback to `index.html` |
| JS/CSS 404 under `/billvice/assets/` | Built without `base: '/billvice/'`, or `dist/` not uploaded |
| Login API fails | `/billing/api/` not proxied to Django |
| Works then jumps to login / blank | Session lost — set `DJANGO_DEBUG=false`, secure cookies, keep same `DJANGO_SECRET_KEY` |
| Data missing after deploy | `db.sqlite3` was overwritten — restore backup / use `DJANGO_DB_PATH` |
