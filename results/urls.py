from django.urls import path

from .views import AssayResultCreateView


urlpatterns = [
    path(
        "<int:pk>/result/",
        AssayResultCreateView.as_view(),
        name="assay_result_create",
    ),
]