from django.contrib import admin

from .models import AssayType, SampleTypeAssay, AssayOrder
from samples.models import Sample
from samples.services import sync_pending_assay_orders


@admin.register(AssayType)
class AssayTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "laboratory_section", "is_biochemical", "is_client_visible", "is_active")
    list_filter = ("category", "laboratory_section", "is_biochemical", "is_client_visible", "is_active")
    search_fields = ("name",)


@admin.register(SampleTypeAssay)
class SampleTypeAssayAdmin(admin.ModelAdmin):
    list_display = ("sample_type", "doc_subtype", "assay")
    list_filter = ("sample_type", "doc_subtype")
    search_fields = ("assay__name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        for sample in Sample.objects.filter(sample_type=obj.sample_type).iterator():
            sync_pending_assay_orders(sample)


from django.contrib import admin
from .models import AssayOrder


@admin.register(AssayOrder)
class AssayOrderAdmin(admin.ModelAdmin):
    list_display = (
        "sample",
        "assay",
        "doc_subtype",
        "status",
    )

    search_fields = (
        "sample__case_code",
        "assay__name",
    )

    list_filter = (
        "status",
        "assay__category",
    )
