from django.contrib import admin
from .models import Sample
from .services import RegisterSampleService
from .forms import SampleForm

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):

    form = SampleForm


    list_display = (
        "case_code",
        "customer",
        "farm",
        "house",
        "sample_type",
        "laboratory",
        "status",
        "received_date",
    )

    search_fields = (
        "case_code",
        "farm__customer__name",
        "farm__name",
        "house__name",
    )

    list_filter = (
        "sample_type",
        "laboratory",
        "status",
        "received_date",
    )

    autocomplete_fields = (
        "house",
    )

    class Media:
        js = (
            "js/sample_admin.js",
            "js/sample_visibility.js",
        )

    @admin.display(
        ordering="farm__customer__name",
        description="Customer",
    )
    def customer(self, obj):
        if obj.farm:
            return obj.farm.customer
        return "-"

    @admin.display(
        ordering="farm__name",
        description="Farm",
    )

    def farm(self, obj):
        return obj.farm if obj.farm else "-"

    def save_model(self, request, obj, form, change):

        if change:
            super().save_model(request, obj, form, change)
            return

        RegisterSampleService.execute(
            form=form,
            user=request.user,
        )