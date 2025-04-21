export DJANGO_SUPERUSER_USERNAME=admin && \
export DJANGO_SUPERUSER_EMAIL=admin@example.com && \
export DJANGO_SUPERUSER_PASSWORD=your_secure_password && \
python manage.py makemigrations app && \
python manage.py migrate && \
python manage.py createsuperuser --noinput \
  --username "$DJANGO_SUPERUSER_USERNAME" \
  --email "$DJANGO_SUPERUSER_EMAIL" && \
gunicorn RTMAS_BACKEND.wsgi:application
