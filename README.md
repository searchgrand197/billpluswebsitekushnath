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

Optional print microservice (Billvice): `python print_service.py` â†’ POST /print, GET /health

