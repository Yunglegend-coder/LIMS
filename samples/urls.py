from django.urls import path
from .views import (
    SampleListView,
    SampleCreateView,
    SampleDetailView,
    SampleFinalResultView,
)


urlpatterns = [
    path("", SampleListView.as_view(), name="sample_list"),
    path("new/", SampleCreateView.as_view(), name="sample_create"),
    path(
        "<int:pk>/",
        SampleDetailView.as_view(),
        name="sample_detail",
    ),
        path(
        "<int:pk>/final-result/",
        SampleFinalResultView.as_view(),
        name="sample_final_result",
    ),
]