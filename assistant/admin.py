from django.contrib import admin

from .models import AppointmentRequest, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "text", "external_message_id", "created_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "clinic",
        "channel",
        "external_user_id",
        "customer_name",
        "bot_paused",
        "updated_at",
    )
    list_filter = ("clinic", "channel", "bot_paused")
    search_fields = ("external_user_id", "customer_name")
    inlines = [MessageInline]


@admin.register(AppointmentRequest)
class AppointmentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "customer_name",
        "phone",
        "service_text",
        "preferred_time_text",
        "clinic",
        "status",
        "created_at",
    )
    list_filter = ("clinic", "status")
    search_fields = ("customer_name", "phone")
    list_editable = ("status",)
