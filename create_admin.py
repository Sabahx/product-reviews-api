from django.contrib.auth.models import User

username = "admin"
password = "admin123"
email = "admin@example.com"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Admin user created.")
else:
    print("Admin user already exists.")
