from django.contrib.auth import get_user_model
User = get_user_model()
username = 'admin'
password = 'admin1234'
email = 'admin@example.com'

try:
    u = User.objects.get(username=username)
    u.set_password(password)
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print(f"Successfully updated password for '{username}' to '{password}'")
except User.DoesNotExist:
    User.objects.create_superuser(username, email, password)
    print(f"Successfully created new superuser '{username}' with password '{password}'")
