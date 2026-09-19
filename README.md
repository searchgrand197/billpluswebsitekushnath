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
2. Upload the whole project **including** `frontend/dist/` (or build on the server)
3. Confirm on server: `ls frontend/dist/index.html`
4. Point nginx at Django for `/billvice/` — see `deploy/nginx.example.conf`
5. Optional: nginx `alias` for `/billvice/assets/` to `frontend/dist/assets/`
6. Set `DEBUG=False`, `DJANGO_SECRET_KEY`, and HTTPS hosts in `CSRF_TRUSTED_ORIGINS`
7. Restart gunicorn/daphne after uploading a new `dist/`

### Common deploy mistakes

| Symptom | Cause |
|---------|--------|
| Blank `/billvice/` page | Old/wrong `index.html` (from `build/`) or assets 404 |
| `/billvice/login` 404 from nginx | nginx serving static SPA without fallback to `index.html` |
| JS/CSS 404 under `/billvice/assets/` | Built without `base: '/billvice/'`, or `dist/` not uploaded |
| Login API fails | `/billing/api/` not proxied to Django |
