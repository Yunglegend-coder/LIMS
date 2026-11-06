from django.contrib import admin
from .models import Customer, CustomerEmailCampaign

# Register your models here.
admin.site.register(Customer)


@admin.register(CustomerEmailCampaign)
class CustomerEmailCampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "sent_by", "recipient_count", "sent_at")
    search_fields = ("subject", "body")
    readonly_fields = ("subject", "body", "sent_by", "recipient_count", "sent_at")
