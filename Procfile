web: gunicorn --chdir backend --bind=0.0.0.0:$PORT --forwarded-allow-ips=* --workers=2 --timeout=60 --access-logfile=- app:app
worker: python backend/worker.py
populate: python backend/populate_cache.py
schema: python backend/schema.py
