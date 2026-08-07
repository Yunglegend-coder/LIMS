from django.urls import path

from .views import (
    CustomerListView,
    CustomerCreateView,
    CustomerDetailView,
    CustomerUpdateView,
    CustomerDeleteView,
)

urlpatterns = [
    path("", CustomerListView.as_view(), name="customer_list"),

    path("new/", CustomerCreateView.as_view(), name="customer_create"),

    path("<int:pk>/", CustomerDetailView.as_view(), name="customer_detail"),

    path("<int:pk>/edit/", CustomerUpdateView.as_view(), name="customer_update"),

    path("<int:pk>/delete/", CustomerDeleteView.as_view(), name="customer_delete"),
]