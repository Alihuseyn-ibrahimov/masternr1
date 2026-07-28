from django.contrib.auth.models import User
from django.db import models

from businesses.models import Business


class BusinessMembership(models.Model):
    """Operator istifadəçisini müəssisə(lər)ə bağlayır — tenant izolyasiyası."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="business_memberships"
    )
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="memberships"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "business"], name="unique_user_business_membership"
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.business.name}"


def businesses_for(user):
    """İstifadəçinin görə bildiyi müəssisələr. Superuser hamısını görür."""
    if user.is_superuser:
        return Business.objects.all()
    return Business.objects.filter(memberships__user=user)
