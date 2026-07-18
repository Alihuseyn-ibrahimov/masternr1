from django.contrib.auth.models import User
from django.db import models

from clinics.models import Clinic


class ClinicMembership(models.Model):
    """Operator istifadəçisini klinika(lar)a bağlayır — tenant izolyasiyası."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="clinic_memberships"
    )
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name="memberships"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "clinic"], name="unique_user_clinic_membership"
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.clinic.name}"


def clinics_for(user):
    """İstifadəçinin görə bildiyi klinikalar. Superuser hamısını görür."""
    if user.is_superuser:
        return Clinic.objects.all()
    return Clinic.objects.filter(memberships__user=user)
