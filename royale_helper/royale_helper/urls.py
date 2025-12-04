from django.contrib import admin
from django.urls import path

from app import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("decks/", views.decks, name="decks"),
    path("recommend/", views.recommend_deck, name="recommend_deck"),
]

