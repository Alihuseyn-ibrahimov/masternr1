from django.urls import path

from . import views

urlpatterns = [
    path("webhook/meta/", views.meta_webhook, name="meta_webhook"),
    path("webhook/manychat/", views.manychat_webhook, name="manychat_webhook"),
]
