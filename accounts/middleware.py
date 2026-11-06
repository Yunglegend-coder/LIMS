from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ObjectDoesNotExist

from .models import UserRole


class LimsLoginRequiredMiddleware:
    """Require authentication for LIMS pages while leaving login/admin public."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info
        static_path = f"/{settings.STATIC_URL.strip('/')}/"
        media_path = f"/{settings.MEDIA_URL.strip('/')}/" if settings.MEDIA_URL.strip("/") else None
        if path.startswith(static_path):
            return None
        if not request.user.is_authenticated:
            if path == settings.LOGIN_URL or path.startswith("/admin/"):
                return None
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)

        try:
            is_receptionist = request.user.profile.role == UserRole.RECEPTIONIST
        except ObjectDoesNotExist:
            is_receptionist = False

        if is_receptionist:
            allowed_paths = {"/samples/new/", "/accounts/logout/", "/accounts/profile/"}
            own_signature_path = f"/media/signatures/user_{request.user.pk}/"
            if path not in allowed_paths and not path.startswith(own_signature_path):
                from django.shortcuts import redirect
                return redirect("sample_create")
            return None

        if path.startswith("/admin/") or (media_path and path.startswith(media_path)):
            return None
        if request.user.is_authenticated:
            return None
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
