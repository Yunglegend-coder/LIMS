from .models import UserNotification


def user_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0, "recent_notifications": []}
    notifications = UserNotification.objects.filter(recipient=request.user)
    return {
        "unread_notification_count": notifications.filter(read_at__isnull=True).count(),
        "recent_notifications": notifications.select_related("sample")[:5],
    }
