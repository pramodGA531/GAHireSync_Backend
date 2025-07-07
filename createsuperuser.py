import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RTMAS_BACKEND.settings')
django.setup()

User = get_user_model()

username = "admin"
password = "admin"
role = "admin"
email = "admin@gmail.com"


if not User.objects.filter( email = email).exists():
    User.objects.create_superuser(username=username, email=email, password=password,role=role)
    print("✅ Superuser created.")
else:
    print("ℹ️ Superuser already exists.")