from django.urls import path

from . import views

urlpatterns = [
    path("webhook/meta/", views.meta_webhook, name="meta_webhook"),
]
