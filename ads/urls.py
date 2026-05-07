from django.urls import path

from . import views

urlpatterns = [
    path("active/", views.active_ad, name="ad-active"),
    path("<int:ad_id>/click/", views.track_click, name="ad-click"),
    path("<int:ad_id>/impression/", views.track_impression, name="ad-impression"),
]
