"""Lokal test üçün demo klinika + operator user yaradır (idempotent).

İstifadə:
    python manage.py seed_demo --phone-number-id 1191771390689506
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from clinics.models import Clinic, Doctor, FAQItem, Service
from inbox.models import ClinicMembership


class Command(BaseCommand):
    help = "Lokal test üçün demo klinika və operator istifadəçisi yaradır"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone-number-id",
            default="1191771390689506",
            help="Meta test nömrəsinin Phone number ID-si",
        )
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demopass123")

    def handle(self, *args, **opts):
        clinic, created = Clinic.objects.update_or_create(
            slug="demo-dent",
            defaults={
                "name": "Demo Dental Klinika",
                "address": "Bakı, Nizami küç. 5",
                "phone": "+994120000000",
                "working_hours_text": "Bazar ertəsi–Şənbə 09:00–19:00, Bazar bağlı",
                "whatsapp_phone_number_id": opts["phone_number_id"],
                "extra_info": "Parkinq var. Kartla ödəniş qəbul olunur.",
                "is_active": True,
            },
        )

        clinic.services.all().delete()
        Service.objects.bulk_create(
            [
                Service(clinic=clinic, name="Diş təmizliyi (professional)", price_text="50 AZN"),
                Service(clinic=clinic, name="Plomb", price_text="40 AZN-dən"),
                Service(clinic=clinic, name="İmplant", price_text="800 AZN-dən"),
                Service(clinic=clinic, name="Diş çəkilməsi", price_text="30 AZN-dən"),
            ]
        )

        clinic.doctors.all().delete()
        Doctor.objects.create(
            clinic=clinic, name="Dr. Aygün Məmmədova", specialty="Ortodont"
        )
        Doctor.objects.create(
            clinic=clinic, name="Dr. Elçin Həsənov", specialty="İmplantoloq"
        )

        clinic.faq_items.all().delete()
        FAQItem.objects.bulk_create(
            [
                FAQItem(
                    clinic=clinic,
                    question="Növbə lazımdır?",
                    answer="Bəli, əvvəlcədən randevu tövsiyə olunur, amma təcili hallarda növbəsiz də qəbul edirik.",
                ),
                FAQItem(
                    clinic=clinic,
                    question="Uşaqları qəbul edirsiniz?",
                    answer="Bəli, pediatrik diş həkimi xidmətimiz var.",
                ),
            ]
        )

        user, _ = User.objects.get_or_create(
            username=opts["username"],
            defaults={"is_staff": True, "is_superuser": True},
        )
        user.set_password(opts["password"])
        user.is_staff = True
        user.is_superuser = True
        user.save()
        ClinicMembership.objects.get_or_create(user=user, clinic=clinic)

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: '{clinic.name}' (phone_number_id={clinic.whatsapp_phone_number_id}); "
                f"operator: {opts['username']} / {opts['password']}"
            )
        )
