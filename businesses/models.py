from django.db import models


class Business(models.Model):
    """Tenant: hər müəssisə (kurs, salon, mərkəz) və onun bilik bazasının kökü."""

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
    staff_label = models.CharField(
        max_length=100,
        default="Komanda",
        help_text='Sistem promptunda komanda bölməsinin başlığı (məs. "Repetitorlar")',
    )
    guardrail_text = models.TextField(
        blank=True,
        help_text=(
            "Bu müəssisə üçün qəti qadağa qaydası (məs. nəticə zəmanəti vermə). "
            "Boş qalsa ümumi ehtiyatlı defolt tətbiq olunur — hər tenant üçün "
            "öz qaydasını yazmaq tövsiyə olunur."
        ),
    )

    # Kanal kimlikləri
    whatsapp_phone_number_id = models.CharField(max_length=100, blank=True)
    instagram_page_id = models.CharField(max_length=100, blank=True)
    access_token = models.TextField(
        blank=True,
        help_text=(
            "Bu müəssisənin Graph API access token-i (WhatsApp/Instagram göndərmə "
            "üçün). Hər tenant öz token-inə malikdir — fərqli WABA/Page-lər eyni "
            "token-i paylaşmır."
        ),
    )

    # Personalın bildiriş aldığı Telegram qrupu
    telegram_chat_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Service(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="services"
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
        return f"{self.name} ({self.business.name})"


class StaffMember(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="staff_members"
    )
    name = models.CharField(max_length=200)
    specialty = models.CharField(max_length=200, blank=True)
    info = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.business.name})"


class FAQItem(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="faq_items"
    )
    question = models.CharField(max_length=300)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question
