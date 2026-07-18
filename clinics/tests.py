from django.test import TestCase

from .models import Clinic, Doctor, FAQItem, Service


def make_clinic(**overrides):
    defaults = dict(
        name="Dent Klinika",
        slug="dent-klinika",
        address="Bakı, Nizami küç. 5",
        phone="+994501234567",
        working_hours_text="B.e-Şənbə 09:00-19:00, Bazar bağlı",
    )
    defaults.update(overrides)
    return Clinic.objects.create(**defaults)


class ClinicModelTests(TestCase):
    def test_str_is_name(self):
        clinic = make_clinic()
        self.assertEqual(str(clinic), "Dent Klinika")

    def test_clinic_is_active_by_default(self):
        clinic = make_clinic()
        self.assertTrue(clinic.is_active)

    def test_related_kb_objects(self):
        clinic = make_clinic()
        Service.objects.create(
            clinic=clinic, name="Diş təmizliyi", price_text="50 AZN"
        )
        Doctor.objects.create(
            clinic=clinic, name="Dr. Aysel Məmmədova", specialty="Ortodont"
        )
        FAQItem.objects.create(
            clinic=clinic,
            question="Kartla ödəniş mümkündürmü?",
            answer="Bəli, bütün kartlar qəbul olunur.",
        )
        self.assertEqual(clinic.services.count(), 1)
        self.assertEqual(clinic.doctors.count(), 1)
        self.assertEqual(clinic.faq_items.count(), 1)

    def test_inactive_service_excluded_from_active_queryset(self):
        clinic = make_clinic()
        Service.objects.create(clinic=clinic, name="Aktiv", price_text="10 AZN")
        Service.objects.create(
            clinic=clinic, name="Köhnə", price_text="5 AZN", is_active=False
        )
        self.assertEqual(clinic.services.filter(is_active=True).count(), 1)
