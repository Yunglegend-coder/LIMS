from django.db import models
from django.conf import settings

# Create your models here.
class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    whatsapp = models.CharField( "WhatsApp Number", max_length=20)
    state = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]


    def __str__(self):
        return self.name


class CustomerEmailCampaign(models.Model):
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="customer_email_campaigns",
    )
    recipient_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} ({self.sent_at:%Y-%m-%d})"
