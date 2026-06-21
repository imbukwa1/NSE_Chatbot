from django.urls import path

from .views import health, search


urlpatterns = [
    path("health/", health, name="kb-health"),
    path("search", search, name="kb-search"),
]
