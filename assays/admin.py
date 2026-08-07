from django.contrib import admin

from .models import AssayType, SampleTypeAssay, AssayOrder


admin.site.register(AssayType)
admin.site.register(SampleTypeAssay)


from django.contrib import admin
from .models import AssayOrder


@admin.register(AssayOrder)
class AssayOrderAdmin(admin.ModelAdmin):
    list_display = (
        "sample",
        "assay",
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
