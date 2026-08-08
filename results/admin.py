from django.contrib import admin
from .models import (
    AssayResult,
    BinaryResult,
    GramStainResult,
    TSIResult,
    ASTResult,
    ASTResultItem,
    InstrumentResult,
    CountResult,
    FungalCultureResult,
    Antibiotic
)

class ASTResultItemInline(admin.TabularInline):
    model = ASTResultItem
    extra = 5

@admin.register(AssayResult)
class AssayResultAdmin(admin.ModelAdmin):
    list_display = (
        "assay_name",
        "case_code",
        "performed_by",
        "verified_by",
        "reported_at",
    )

    search_fields = (
        "assay_order__sample__case_code",
        "assay_order__assay__name",
    )

    list_filter = (
        "assay_order__assay__category",
        "reported_at",
    )

    autocomplete_fields = (
        "assay_order",
        "performed_by",
        "verified_by",
    )

    def case_code(self, obj):
        return obj.assay_order.sample.case_code

    case_code.short_description = "Case Code"

    def assay_name(self, obj):
        return obj.assay_order.assay.name

    assay_name.short_description = "Assay"

@admin.register(BinaryResult)
class BinaryResultAdmin(admin.ModelAdmin):
    list_display = (
        "assay",
        "case_code",
        "result",
    )

    search_fields = (
        "assay_result__assay_order__sample__case_code",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

    def assay(self, obj):
        return obj.assay_result.assay_order.assay.name

@admin.register(GramStainResult)
class GramStainResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "result",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

@admin.register(TSIResult)
class TSIResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "result",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code


@admin.register(ASTResult)
class ASTResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "assay",
    )

    inlines = [ASTResultItemInline]

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

    def assay(self, obj):
        return obj.assay_result.assay_order.assay.name

@admin.register(InstrumentResult)
class InstrumentResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "interpretation",
        "ct_value",
        "titre",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

@admin.register(CountResult)
class CountResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "count",
        "unit",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

@admin.register(FungalCultureResult)
class FungalCultureResultAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "colony_count",
        "organism_name",
    )

    search_fields = (
        "organism_name",
        "assay_result__assay_order__sample__case_code",
    )

    def case_code(self, obj):
        return obj.assay_result.assay_order.sample.case_code

@admin.register(Antibiotic)
class AntibioticAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )

@admin.register(ASTResultItem)
class ASTResultItemAdmin(admin.ModelAdmin):

    list_display = (
        "ast_result",
        "antibiotic",
        "interpretation",
    )

    list_filter = (
        "interpretation",
    )

    search_fields = (
        "antibiotic__code",
        "antibiotic__name",
        "ast_result__assay_result__assay_order__sample__case_code",
    )

