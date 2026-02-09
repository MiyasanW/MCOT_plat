import os, django, sys
from django.test import Client

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def debug_catalog():
    print("--- Debugging Catalog Page ---")
    c = Client()
    try:
        response = c.get('/catalog/')
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print("Error Content:")
            # decode if possible, or print raw
            print(response.content.decode('utf-8'))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_catalog()
