from django.urls import path

from .views import SampleListView, SampleCreateView

urlpatterns = [
    path("", SampleListView.as_view(), name="sample_list"),
    path("new/", SampleCreateView.as_view(), name="sample_create"),
]