from django.urls import path

from .views import (
    AssayResultCreateView,
    PendingResultsView,
    PendingAssayResultsView,
    LaboratoryResultsDashboardView,
)


urlpatterns = [

    # ---------------------------------------------------------
    # Individual assay result entry
    # ---------------------------------------------------------

    path(
        "<int:pk>/result/",
        AssayResultCreateView.as_view(),
        name="assay_result_create",
    ),

    # ---------------------------------------------------------
    # Pending results by laboratory
    # Example:
    # /results/pending/MICRO/
    # ---------------------------------------------------------

    path(
        "pending/<str:laboratory>/",
        PendingResultsView.as_view(),
        name="pending_results",
    ),

    # ---------------------------------------------------------
    # Pending results for a specific assay
    # Example:
    # /results/pending/MICRO/5/
    # ---------------------------------------------------------

    path(
        "pending/<str:laboratory>/<int:assay_pk>/",
        PendingAssayResultsView.as_view(),
        name="pending_assay_results",
    ),

    # ---------------------------------------------------------
    # Laboratory results dashboard
    # ---------------------------------------------------------

    path(
        "laboratory-results/",
        LaboratoryResultsDashboardView.as_view(),
        name="laboratory_results_dashboard",
    ),
]