import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("--- Testing Availability API ---")
    # 1. Get a product ID (assuming ID 1 exists, created by migration/fixture if any)
    # Since we have a fresh DB, we might need to create one first manually or via shell.
    # But let's assume valid product_id=1 for now or check response.
    
    start = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 10:00")
    end = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d 10:00")
    
    url = f"{BASE_URL}/api/check-availability/?product_id=1&start={start}&end={end}"
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_api()
