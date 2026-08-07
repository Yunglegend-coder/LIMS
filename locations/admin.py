from django.contrib import admin

from .models import Farm, House


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "customer",
        "state",
        "active",
    )

    list_filter = (
        "active",
        "state",
    )

    search_fields = (
        "name",
        "customer__name",
    )


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "farm",
        "bird_type",
        "capacity",
        "active",
    )

    list_filter = (
        "active",
        "bird_type",
    )

    search_fields = (
        "name",
        "farm__name",
        "farm__customer__name",
    )

    autocomplete_fields = (
        "farm",
    )