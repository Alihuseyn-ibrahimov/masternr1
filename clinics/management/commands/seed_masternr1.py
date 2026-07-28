"""Master NR 1 (magistratura/doktorantura hazırlıq kursu) pilot demo klinikası.

İstifadə:
    python manage.py seed_masternr1 --phone-number-id 1191771390689506

QEYD: Aşağıdakı qiymətlər/proqramlar PLACEHOLDER-dir — real demo/görüşdən əvvəl
Django admin-dən həqiqi məlumatlarla (qiymət, qrup vaxtları, FAQ) əvəz edilməlidir.

Eyni Meta test WhatsApp nömrəsi yalnız BİR klinikaya bağlana bilər (routing
whatsapp_phone_number_id ilə tək-tək axtarılır), ona görə köhnə demo-dent
klinikasının nömrəsi bu skriptdə boşaldılır.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from clinics.models import Clinic, Doctor, FAQItem, Service
from inbox.models import ClinicMembership


class Command(BaseCommand):
    help = "Master NR 1 tədris mərkəzi üçün demo klinika və operator istifadəçisi yaradır"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone-number-id",
            default="1191771390689506",
            help="Meta test nömrəsinin Phone number ID-si",
        )
        parser.add_argument("--username", default="masternr1")
        parser.add_argument("--password", default="demopass123")

    def handle(self, *args, **opts):
        # Eyni test nömrəsi ilə routing konflikti olmasın deyə köhnə demo
        # klinikanın nömrəsini boşaldırıq (yalnız lokal test üçündür).
        Clinic.objects.filter(
            whatsapp_phone_number_id=opts["phone_number_id"]
        ).exclude(slug="master-nr-1").update(whatsapp_phone_number_id="")

        clinic, created = Clinic.objects.update_or_create(
            slug="master-nr-1",
            defaults={
                "name": "Master NR 1 Tədris Mərkəzi",
                "address": "Bakı",  # TODO: görüşdən sonra dəqiq ünvanla əvəz et
                "phone": "",  # TODO: görüşdən sonra doldur
                "working_hours_text": "B.e-Şənbə 10:00-19:00",  # TODO: dəqiqləşdir
                "whatsapp_phone_number_id": opts["phone_number_id"],
                "extra_info": (
                    "Magistratura, Doktorantura və Dövlət Qulluğu imtahanlarına "
                    "hazırlıq kursları. Yüzlərlə uğurlu məzun."
                ),
                "staff_label": "Repetitorlar / Müəllimlər",
                "guardrail_text": (
                    "Qəbul faizini, imtahan nəticəsini və ya konkret balı heç vaxt "
                    "zəmanət kimi vəd etmə. Müştəri 'məni qəbul edərsiniz?', "
                    "'zəmanət verirsiniz?' kimi sual versə, bildir ki, nəticə "
                    "şagirdin öz hazırlığından asılıdır, kurs isə keyfiyyətli "
                    "hazırlıq təmin edir; konkret sual üçün operatora yönləndir."
                ),
                "is_active": True,
            },
        )

        clinic.services.all().delete()
        Service.objects.bulk_create(
            [
                Service(
                    clinic=clinic,
                    name="Magistratura hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
                Service(
                    clinic=clinic,
                    name="Doktorantura hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
                Service(
                    clinic=clinic,
                    name="Dövlət Qulluğu (DQ) hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
            ]
        )

        clinic.doctors.all().delete()
        Doctor.objects.create(
            clinic=clinic,
            name="Repetitor (nümunə)",
            specialty="Fənn (görüşdən sonra dəqiqləşdir)",
        )

        clinic.faq_items.all().delete()
        FAQItem.objects.bulk_create(
            [
                FAQItem(
                    clinic=clinic,
                    question="Dərslər online, yoxsa oflayn keçirilir?",
                    answer="TODO: görüşdən sonra doldur.",
                ),
                FAQItem(
                    clinic=clinic,
                    question="Qrup nə vaxt başlayır?",
                    answer="TODO: görüşdən sonra doldur.",
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
                f"operator: {opts['username']} / {opts['password']}\n"
                "DİQQƏT: qiymət/ünvan/FAQ sahələri PLACEHOLDER-dir — "
                "Django admin-dən real məlumatla doldur."
            )
        )
