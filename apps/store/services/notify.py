import requests
from django.conf import settings

def send_line_notify(message, token=None):
    """
    ส่งการแจ้งเตือนพนักงานผ่าน LINE Notify
    ใช้ Library 'requests' ในการยิง API
    """
    if not token and hasattr(settings, 'LINE_NOTIFY_TOKEN'):
        token = settings.LINE_NOTIFY_TOKEN
        
    if not token:
        # ถ้าไม่มี Token ให้ข้ามไป (เช่น Environment Dev)
        print(f"[Mock Line Notify] {message}")
        return False

    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    data = {'message': message}
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error sending Line Notify: {e}")
        return False
