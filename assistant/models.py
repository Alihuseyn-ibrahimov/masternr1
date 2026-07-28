from django.db import models

from businesses.models import Business


class Conversation(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="conversations"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    external_user_id = models.CharField(
        max_length=200,
        help_text="Kanaldakı müştəri identifikatoru (WA nömrəsi / IG user ID)",
    )
    bot_paused = models.BooleanField(
        default=False,
        help_text="True olduqda bot cavab vermir, operator danışır",
    )
    customer_name = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "channel", "external_user_id"],
                name="unique_conversation_per_channel_user",
            )
        ]

    def __str__(self):
        return f"{self.business.name} / {self.channel} / {self.external_user_id}"


class Message(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Müştəri"
        BOT = "bot", "Bot"
        OPERATOR = "operator", "Operator"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    text = models.TextField()
    external_message_id = models.CharField(
        max_length=200,
        blank=True,
        help_text="Kanalın mesaj ID-si — webhook dedup üçün",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"[{self.role}] {self.text[:50]}"


class CustomerRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yeni"
        CONFIRMED = "confirmed", "Təsdiqləndi"
        REJECTED = "rejected", "İmtina"

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="customer_requests"
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_requests",
    )
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    service_text = models.CharField(
        max_length=300, blank=True, help_text="Müştərinin istədiyi xidmət"
    )
    preferred_time_text = models.CharField(
        max_length=300, blank=True, help_text="Müştərinin istədiyi vaxt, sərbəst mətn"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer_name} — {self.service_text or 'sorğu'} ({self.status})"
