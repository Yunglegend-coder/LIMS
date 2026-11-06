import json

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import OuterRef, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView, View, TemplateView, UpdateView

from .models import StaffMessage, UserNotification, UserProfile, VoiceCall, VoiceCallCandidate
from .forms import UserSignatureForm

User = get_user_model()


class UserSignatureView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserSignatureForm
    template_name = "accounts/profile_signature.html"

    def get_object(self, queryset=None):
        profile, _created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, "Your report signature was saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "accounts/notifications.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return UserNotification.objects.filter(recipient=self.request.user).select_related(
            "sample", "sample__farm", "sample__farm__customer"
        )


class NotificationReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notification = get_object_or_404(
            UserNotification,
            pk=kwargs["pk"],
            recipient=request.user,
        )
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return redirect("sample_detail", pk=notification.sample_id)


class MessageCenterView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/message_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["users"] = User.objects.filter(is_active=True).exclude(pk=user.pk).order_by(
            "first_name", "username"
        )
        context["announcements"] = StaffMessage.objects.filter(
            recipient__isnull=True
        ).select_related("sender").order_by("-created_at")[:30]
        other_users = User.objects.filter(is_active=True).exclude(pk=user.pk)
        last_message = StaffMessage.objects.filter(
            Q(sender=OuterRef("pk"), recipient=user)
            | Q(sender=user, recipient=OuterRef("pk"))
        ).order_by("-created_at")
        context["recent_conversations"] = other_users.annotate(
            last_message_at=Subquery(last_message.values("created_at")[:1]),
            last_message_body=Subquery(last_message.values("body")[:1]),
            last_message_sender_id=Subquery(last_message.values("sender_id")[:1]),
        ).filter(last_message_at__isnull=False).order_by("-last_message_at")
        return context

    def post(self, request, *args, **kwargs):
        recipient_id = request.POST.get("recipient")
        body = request.POST.get("body", "").strip()
        if not body or len(body) > 4000:
            messages.error(request, "Enter a message of 1 to 4,000 characters.")
            return redirect("message_center")
        recipient = get_object_or_404(User, pk=recipient_id, is_active=True)
        if recipient.pk == request.user.pk:
            messages.error(request, "Choose another user to message.")
            return redirect("message_center")
        StaffMessage.objects.create(sender=request.user, recipient=recipient, body=body)
        messages.success(request, f"Message sent to {recipient.get_full_name() or recipient.username}.")
        return redirect("direct_message", user_id=recipient.pk)


class DirectMessageView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/direct_message.html"

    def dispatch(self, request, *args, **kwargs):
        self.other_user = get_object_or_404(
            User, pk=kwargs["user_id"], is_active=True
        )
        if self.other_user.pk == request.user.pk:
            return redirect("message_center")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["other_user"] = self.other_user
        context["messages_list"] = StaffMessage.objects.filter(
            Q(sender=self.request.user, recipient=self.other_user)
            | Q(sender=self.other_user, recipient=self.request.user)
        ).select_related("sender")
        return context

    def post(self, request, *args, **kwargs):
        body = request.POST.get("body", "").strip()
        if not body or len(body) > 4000:
            messages.error(request, "Enter a message of 1 to 4,000 characters.")
        else:
            StaffMessage.objects.create(
                sender=request.user, recipient=self.other_user, body=body
            )
        return redirect("direct_message", user_id=self.other_user.pk)


class AnnouncementCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        body = request.POST.get("body", "").strip()
        if not body or len(body) > 4000:
            messages.error(request, "Enter an announcement of 1 to 4,000 characters.")
        else:
            StaffMessage.objects.create(sender=request.user, body=body)
            messages.success(request, "Announcement posted for all LIMS users.")
        return redirect("message_center")


def _json_payload(request):
    if len(request.body) > 128_000:
        return None
    try:
        return json.loads(request.body or b"{}")
    except (TypeError, ValueError, UnicodeDecodeError):
        return None


class VoiceCallStateView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        other = get_object_or_404(User, pk=user_id, is_active=True)
        call = VoiceCall.objects.filter(
            Q(caller=request.user, callee=other) | Q(caller=other, callee=request.user)
        ).first()
        if call is None:
            return JsonResponse({"call": None})
        if call.status == VoiceCall.Status.RINGING and (timezone.now() - call.created_at).total_seconds() > 90:
            marked_missed = VoiceCall.objects.filter(
                pk=call.pk, status=VoiceCall.Status.RINGING
            ).update(status=VoiceCall.Status.MISSED, updated_at=timezone.now())
            if marked_missed:
                StaffMessage.objects.create(
                    sender=call.caller,
                    recipient=call.callee,
                    body="Missed voice call",
                )
            call.refresh_from_db()
        return JsonResponse({
            "call": {
                "id": call.pk,
                "caller_id": call.caller_id,
                "callee_id": call.callee_id,
                "status": call.status,
                "offer": call.offer,
                "answer": call.answer,
                "candidates": list(call.candidates.values("id", "sender_id", "candidate")),
            }
        })


class VoiceCallStartView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id, is_active=True)
        payload = _json_payload(request)
        if other.pk == request.user.pk or not isinstance(payload, dict) or not isinstance(payload.get("offer"), dict):
            return JsonResponse({"error": "A valid call offer and another active user are required."}, status=400)
        existing = VoiceCall.objects.filter(
            Q(caller=request.user, callee=other) | Q(caller=other, callee=request.user),
            status__in=[VoiceCall.Status.RINGING, VoiceCall.Status.ACTIVE],
        ).first()
        if existing and existing.status == VoiceCall.Status.RINGING and (timezone.now() - existing.created_at).total_seconds() > 90:
            marked_missed = VoiceCall.objects.filter(
                pk=existing.pk, status=VoiceCall.Status.RINGING
            ).update(status=VoiceCall.Status.MISSED, updated_at=timezone.now())
            if marked_missed:
                StaffMessage.objects.create(
                    sender=existing.caller,
                    recipient=existing.callee,
                    body="Missed voice call",
                )
            existing = None
        if existing:
            return JsonResponse({"error": "There is already a call in progress with this user."}, status=409)
        call = VoiceCall.objects.create(caller=request.user, callee=other, offer=payload["offer"])
        return JsonResponse({"call_id": call.pk}, status=201)


class VoiceCallAcceptView(LoginRequiredMixin, View):
    def post(self, request, call_id):
        call = get_object_or_404(VoiceCall, pk=call_id, callee=request.user)
        payload = _json_payload(request)
        if call.status != VoiceCall.Status.RINGING or not isinstance(payload, dict) or not isinstance(payload.get("answer"), dict):
            return JsonResponse({"error": "This call cannot be accepted."}, status=409)
        call.answer = payload["answer"]
        call.status = VoiceCall.Status.ACTIVE
        call.save(update_fields=["answer", "status", "updated_at"])
        return JsonResponse({"ok": True})


class VoiceCallCandidateView(LoginRequiredMixin, View):
    def post(self, request, call_id):
        call = get_object_or_404(VoiceCall, pk=call_id)
        if request.user.pk not in (call.caller_id, call.callee_id) or call.status == VoiceCall.Status.ENDED:
            return JsonResponse({"error": "You cannot signal this call."}, status=403)
        payload = _json_payload(request)
        candidate = payload.get("candidate") if isinstance(payload, dict) else None
        if not isinstance(candidate, dict) or len(json.dumps(candidate)) > 12000:
            return JsonResponse({"error": "Invalid connection candidate."}, status=400)
        VoiceCallCandidate.objects.create(call=call, sender=request.user, candidate=candidate)
        return JsonResponse({"ok": True}, status=201)


class VoiceCallEndView(LoginRequiredMixin, View):
    def post(self, request, call_id):
        call = get_object_or_404(VoiceCall, pk=call_id)
        if request.user.pk not in (call.caller_id, call.callee_id):
            return JsonResponse({"error": "You cannot end this call."}, status=403)
        if call.status != VoiceCall.Status.ENDED:
            call.status = VoiceCall.Status.ENDED
            call.save(update_fields=["status", "updated_at"])
        return JsonResponse({"ok": True})
