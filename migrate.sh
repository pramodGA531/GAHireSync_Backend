set -e  

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Checking for missing tables..."
python <<EOF
from django.apps import apps
from django.db import connection

# Retrieve all table names from the database
existing_tables = connection.introspection.table_names()

# Iterate through all models in the project
for model in apps.get_models():
    table_name = model._meta.db_table
    if table_name not in existing_tables:
        print(f"Missing table: {table_name}")
EOF

echo "Starting Gunicorn..."
gunicorn RTMAS_BACKEND.wsgi
