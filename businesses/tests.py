from django.test import TestCase

from .models import Business, FAQItem, Service, StaffMember


def make_business(**overrides):
    defaults = dict(
        name="Test Tədris Mərkəzi",
        slug="test-tedris-merkezi",
        address="Bakı, Nizami küç. 5",
        phone="+994501234567",
        working_hours_text="B.e-Şənbə 10:00-19:00, Bazar bağlı",
    )
    defaults.update(overrides)
    return Business.objects.create(**defaults)


class BusinessModelTests(TestCase):
    def test_str_is_name(self):
        business = make_business()
        self.assertEqual(str(business), "Test Tədris Mərkəzi")

    def test_business_is_active_by_default(self):
        business = make_business()
        self.assertTrue(business.is_active)

    def test_related_kb_objects(self):
        business = make_business()
        Service.objects.create(
            business=business, name="Magistratura hazırlığı", price_text="300 AZN"
        )
        StaffMember.objects.create(
            business=business, name="Aysel Məmmədova", specialty="Riyaziyyat"
        )
        FAQItem.objects.create(
            business=business,
            question="Kartla ödəniş mümkündürmü?",
            answer="Bəli, bütün kartlar qəbul olunur.",
        )
        self.assertEqual(business.services.count(), 1)
        self.assertEqual(business.staff_members.count(), 1)
        self.assertEqual(business.faq_items.count(), 1)

    def test_inactive_service_excluded_from_active_queryset(self):
        business = make_business()
        Service.objects.create(business=business, name="Aktiv", price_text="10 AZN")
        Service.objects.create(
            business=business, name="Köhnə", price_text="5 AZN", is_active=False
        )
        self.assertEqual(business.services.filter(is_active=True).count(), 1)
