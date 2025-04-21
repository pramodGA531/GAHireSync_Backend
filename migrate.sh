python manage.py makemigrations app && \
python manage.py migrate && \
python manage.py showmigrations && \
gunicorn RTMAS_BACKEND.wsgi:application
