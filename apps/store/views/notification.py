import re

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from apps.store.models import Notification

@login_required
@require_GET
def get_notifications_api(request):
    """
    API: Fetch latest notifications for the logged-in user.
    """
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    data = []
    for notif in notifications:
        link = notif.link
        
        # Rewrite legacy admin links to the new Staff Summary Dashboard
        if link and request.user.is_staff:
            link = re.sub(r'/admin/store/booking/(\d+)/change/?', r'/staff/booking/\1/summary/', link)
            
        data.append({
            'id': notif.id,
            'message': notif.message,
            'link': link,
            'is_read': notif.is_read,
            'type': notif.notification_type,
            'created_at': notif.created_at.strftime("%d/%m %H:%M")
        })
        
    return JsonResponse({
        'success': True,
        'notifications': data,
        'unread_count': unread_count
    })

@login_required
@require_POST
def mark_notification_read_api(request, notification_id=None):
    """
    API: Mark a specific notification or all notifications as read.
    """
    if notification_id:
        try:
            notif = Notification.objects.get(id=notification_id, recipient=request.user)
            notif.is_read = True
            notif.save()
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Not found'}, status=404)
    else:
        # Mark all as read
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        
    return JsonResponse({'success': True})
