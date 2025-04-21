python manage.py makemigrations app && \
python manage.py migrate && \
gunicorn RTMAS_BACKEND.wsgi:application
