from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        try:
            role = request.user.profile.role
        except ObjectDoesNotExist:
            return HttpResponseForbidden("A LIMS role has not been assigned to this account.")
        if role == "RECEPTIONIST" and not getattr(self, "allow_receptionist", False):
            return HttpResponseForbidden("You do not have permission to access this page.")
        return super().dispatch(request, *args, **kwargs)
