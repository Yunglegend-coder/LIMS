from django.urls import path

from .views import (
    AssayResultCreateView,
    PendingResultsView,
    PendingAssayResultsView,
    LaboratoryResultsDashboardView,
    CompletedResultsView,
    SampleFinalResultView,
    AssayResultEditView,
    SampleReportPDFView,
    SampleReportDOCXView,
    SampleReportDeliveryView,
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
    path(
        "result/<int:pk>/edit/",
        AssayResultEditView.as_view(),
        name="assay_result_edit",
    ),

    # =========================================================
    # COMPLETED RESULTS
    # =========================================================

    # ---------------------------------------------------------
    # Final result for ONE SAMPLE
    #
    # IMPORTANT:
    # This must come BEFORE <str:laboratory>
    #
    # Example:
    # /results/completed/10/
    # ---------------------------------------------------------

    path(
        "completed/<int:pk>/",
        SampleFinalResultView.as_view(),
        name="sample_final_result",
    ),
    path(
        "report/<int:pk>/pdf/",
        SampleReportPDFView.as_view(),
        name="sample_report_pdf",
    ),
    path(
        "report/<int:pk>/docx/",
        SampleReportDOCXView.as_view(),
        name="sample_report_docx",
    ),
    path(
        "report/<int:pk>/send/<str:channel>/",
        SampleReportDeliveryView.as_view(),
        name="sample_report_send",
    ),

    # ---------------------------------------------------------
    # Completed samples for a laboratory
    #
    # Example:
    # /results/completed/MICRO/
    # ---------------------------------------------------------

    path(
        "completed/<str:laboratory>/",
        CompletedResultsView.as_view(),
        name="completed_results",
    ),
]
