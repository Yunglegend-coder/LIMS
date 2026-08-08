from django.urls import path
from .views import houses_by_farm

urlpatterns = [
    path(
        "houses/",
        houses_by_farm,
        name="houses_by_farm",
    ),
]