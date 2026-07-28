"""Master NR 1 (magistratura/doktorantura hazırlıq kursu) pilot demo müəssisəsi.

İstifadə:
    python manage.py seed_masternr1 --phone-number-id 1191771390689506

QEYD: Aşağıdakı qiymətlər/proqramlar PLACEHOLDER-dir — real demo/görüşdən əvvəl
Django admin-dən həqiqi məlumatlarla (qiymət, qrup vaxtları, FAQ) əvəz edilməlidir.

Eyni Meta test WhatsApp nömrəsi yalnız BİR müəssisəyə bağlana bilər (routing
whatsapp_phone_number_id ilə tək-tək axtarılır), ona görə köhnə demo-dent
müəssisəsinin nömrəsi bu skriptdə boşaldılır.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from businesses.models import Business, StaffMember, FAQItem, Service
from inbox.models import BusinessMembership


class Command(BaseCommand):
    help = "Master NR 1 tədris mərkəzi üçün demo müəssisə və operator istifadəçisi yaradır"

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
        # müəssisənin nömrəsini boşaldırıq (yalnız lokal test üçündür).
        Business.objects.filter(
            whatsapp_phone_number_id=opts["phone_number_id"]
        ).exclude(slug="master-nr-1").update(whatsapp_phone_number_id="")

        business, created = Business.objects.update_or_create(
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

        business.services.all().delete()
        Service.objects.bulk_create(
            [
                Service(
                    business=business,
                    name="Magistratura hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
                Service(
                    business=business,
                    name="Doktorantura hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
                Service(
                    business=business,
                    name="Dövlət Qulluğu (DQ) hazırlıq kursu",
                    price_text="Qiymət (görüşdən sonra doldurulacaq)",
                ),
            ]
        )

        business.staff_members.all().delete()
        StaffMember.objects.create(
            business=business,
            name="Repetitor (nümunə)",
            specialty="Fənn (görüşdən sonra dəqiqləşdir)",
        )

        business.faq_items.all().delete()
        FAQItem.objects.bulk_create(
            [
                FAQItem(
                    business=business,
                    question="Dərslər online, yoxsa oflayn keçirilir?",
                    answer="TODO: görüşdən sonra doldur.",
                ),
                FAQItem(
                    business=business,
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
        BusinessMembership.objects.get_or_create(user=user, business=business)

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: '{business.name}' (phone_number_id={business.whatsapp_phone_number_id}); "
                f"operator: {opts['username']} / {opts['password']}\n"
                "DİQQƏT: qiymət/ünvan/FAQ sahələri PLACEHOLDER-dir — "
                "Django admin-dən real məlumatla doldur."
            )
        )
