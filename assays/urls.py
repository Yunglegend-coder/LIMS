from django.urls import path

from .views import (
    AssayOrderDetailView,
    AssayOrderStartView,
)


urlpatterns = [
    path(
        "<int:pk>/",
        AssayOrderDetailView.as_view(),
        name="assay_order_detail",
    ),

    path(
        "<int:pk>/start/",
        AssayOrderStartView.as_view(),
        name="assay_order_start",
    ),
]