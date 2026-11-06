import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from samples.models import Sample


def user_signature_upload_to(instance, filename):
    return f"signatures/user_{instance.user_id}/{os.path.basename(filename)}"


class UserRole(models.TextChoices):
    VET_DOCTOR = "VET_DOCTOR", "Vet doctor"
    LAB_SCIENTIST = "LAB_SCIENTIST", "Laboratory scientist"
    RECEPTIONIST = "RECEPTIONIST", "Receptionist"
    MANAGER = "MANAGER", "Manager"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.RECEPTIONIST,
    )
    whatsapp = models.CharField(max_length=20, blank=True)
    signature = models.ImageField(
        upload_to=user_signature_upload_to,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png"])],
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class UserNotification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lims_notifications",
    )
    sample = models.ForeignKey(
        Sample,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=160)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.recipient}"


class StaffMessage(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_staff_messages",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_staff_messages",
        null=True,
        blank=True,
        help_text="Leave empty for a message visible to all LIMS users.",
    )
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["sender", "recipient", "created_at"])]

    @property
    def is_announcement(self):
        return self.recipient_id is None

    def __str__(self):
        destination = "announcement" if self.is_announcement else str(self.recipient)
        return f"{self.sender} → {destination}: {self.body[:50]}"


class VoiceCall(models.Model):
    class Status(models.TextChoices):
        RINGING = "RINGING", "Ringing"
        ACTIVE = "ACTIVE", "Active"
        MISSED = "MISSED", "Missed"
        ENDED = "ENDED", "Ended"

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="placed_voice_calls",
    )
    callee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_voice_calls",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RINGING)
    offer = models.JSONField()
    answer = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class VoiceCallCandidate(models.Model):
    call = models.ForeignKey(VoiceCall, on_delete=models.CASCADE, related_name="candidates")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    candidate = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
