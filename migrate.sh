python manage.py migrate app 0000 --fake
python manage.py migrate app
gunicorn RTMAS_BACKEND.wsgi