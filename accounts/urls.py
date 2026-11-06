from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    AnnouncementCreateView,
    DirectMessageView,
    MessageCenterView,
    NotificationListView,
    NotificationReadView,
    VoiceCallAcceptView,
    VoiceCallCandidateView,
    VoiceCallEndView,
    VoiceCallStartView,
    VoiceCallStateView,
    UserSignatureView,
)

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", UserSignatureView.as_view(), name="account_profile"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification_read"),
    path("messages/", MessageCenterView.as_view(), name="message_center"),
    path("messages/announcements/", AnnouncementCreateView.as_view(), name="announcement_create"),
    path("messages/<int:user_id>/", DirectMessageView.as_view(), name="direct_message"),
    path("messages/<int:user_id>/call/state/", VoiceCallStateView.as_view(), name="voice_call_state"),
    path("messages/<int:user_id>/call/start/", VoiceCallStartView.as_view(), name="voice_call_start"),
    path("messages/call/<int:call_id>/accept/", VoiceCallAcceptView.as_view(), name="voice_call_accept"),
    path("messages/call/<int:call_id>/candidate/", VoiceCallCandidateView.as_view(), name="voice_call_candidate"),
    path("messages/call/<int:call_id>/end/", VoiceCallEndView.as_view(), name="voice_call_end"),
]
