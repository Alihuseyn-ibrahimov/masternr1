from django.db import models


class Clinic(models.Model):
    """Tenant: hər klinika/salon və onun bilik bazasının kökü."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    working_hours_text = models.CharField(max_length=300, blank=True)
    extra_info = models.TextField(
        blank=True,
        help_text="Sərbəst əlavə məlumat (parkinq, kampaniyalar və s.)",
    )

    # Kanal kimlikləri
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True)
    instagram_page_id = models.CharField(max_length=100, blank=True)

    # Personalın bildiriş aldığı Telegram qrupu
    telegram_chat_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Service(models.Model):
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=200)
    price_text = models.CharField(
        max_length=100,
        blank=True,
        help_text='Sərbəst format: "50 AZN", "800 AZN-dən" və s.',
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.clinic.name})"


class Doctor(models.Model):
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name="doctors"
    )
    name = models.CharField(max_length=200)
    specialty = models.CharField(max_length=200, blank=True)
    info = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.clinic.name})"


class FAQItem(models.Model):
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name="faq_items"
    )
    question = models.CharField(max_length=300)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question
