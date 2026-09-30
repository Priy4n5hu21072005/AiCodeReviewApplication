from django.urls import path
from .views import review_repo

urlpatterns = [
    path("review/",review_repo),
]
