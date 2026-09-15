# billpluswebsitekushnath

# Merged Kushnath project (Live ecommerce + Billvice POS)

## Run

```bash
cd merged
# use the live venv (or create a new one from requirements.txt)
..\kushnathlive\kushnathwebsite\venv\Scripts\python.exe manage.py runserver
```

- Storefront: http://127.0.0.1:8000/
- Billvice POS: http://127.0.0.1:8000/billvice/
- Admin: http://127.0.0.1:8000/admin/

Optional print microservice (Billvice): `python print_service.py` -> POST /print, GET /health

## Billvice frontend build (required for /billvice/)

```bash
cd frontend
npm install
npm run build
```

Creates `frontend/dist/` with `base: /billvice/` and React Router `basename="/billvice"`.
If this folder is missing or built without `/billvice`, the POS page will be blank.

## Production checklist

1. Upload `frontend/dist/` to the server (after `npm run build`)
2. Proxy `/billvice/` to Django — nginx/Apache must not serve a storefront SPA fallback for this path
3. See `deploy/nginx.example.conf`
4. Set `DEBUG=False`, `DJANGO_SECRET_KEY`, and HTTPS in `CSRF_TRUSTED_ORIGINS`

