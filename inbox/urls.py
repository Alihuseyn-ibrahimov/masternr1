from django.urls import path

from . import views

app_name = "inbox"

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("customer_requests/", views.request_list, name="request_list"),
    path("c/<int:pk>/", views.conversation_detail, name="conversation_detail"),
    path("c/<int:pk>/reply/", views.send_operator_reply, name="send_reply"),
    path("c/<int:pk>/toggle-bot/", views.toggle_bot, name="toggle_bot"),
]
