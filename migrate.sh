export DJANGO_SUPERUSER_USERNAME=admin && \
export DJANGO_SUPERUSER_EMAIL=admin@example.com && \
export DJANGO_SUPERUSER_PASSWORD=admin && \
python manage.py migrate && \
python manage.py createsuperuser --noinput \
  --username "$DJANGO_SUPERUSER_USERNAME" \
  --email "$DJANGO_SUPERUSER_EMAIL" && \
gunicorn RTMAS_BACKEND.wsgi:application
# gunicorn RTMAS_BACKEND.wsgi:application --bind 0.0.0.0:$PORT