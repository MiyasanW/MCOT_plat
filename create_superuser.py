from django.contrib.auth import get_user_model
User = get_user_model()
username = 'admin_dev'
email = 'admin@example.com'
password = 'password123'

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"Superuser '{username}' created.")
else:
    print(f"Superuser '{username}' already exists.")
