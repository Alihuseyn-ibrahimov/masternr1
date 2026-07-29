"""DVX Tədris Mərkəzi (vergi/mühasibatlıq təlimləri) — 2-ci tenant.

İstifadə:
    python manage.py seed_dvx
    python manage.py seed_dvx --instagram-page-id 17841400000000000

QEYD: Qiymət/proqram/FAQ sahələri PLACEHOLDER-dir — şirkətdən real məlumat
alınandan sonra Django admin-dən doldurulmalıdır. `instagram_page_id` Meta
qoşulması tamamlananda verilir (Faza B).

Master NR 1 tenant-ına TOXUNULMUR — iki tenant paralel işləyir.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from businesses.models import Business, FAQItem, Service, StaffMember
from inbox.models import BusinessMembership


class Command(BaseCommand):
    help = "DVX Tədris Mərkəzi üçün tenant və operator istifadəçisi yaradır"

    def add_arguments(self, parser):
        parser.add_argument(
            "--instagram-page-id",
            default="",
            help="Meta qoşulmasından sonra alınan Instagram page ID",
        )
        parser.add_argument("--username", default="dvx")
        parser.add_argument("--password", default="demopass123")

    def handle(self, *args, **opts):
        clash = (
            Business.objects.filter(
                instagram_page_id=opts["instagram_page_id"]
            ).exclude(slug="dvx-tedris-merkezi")
            if opts["instagram_page_id"]
            else Business.objects.none()
        )
        if clash.exists():
            self.stderr.write(
                "XƏTA: bu instagram_page_id başqa tenant-dadır — əvvəl onu boşalt."
            )
            return

        business, created = Business.objects.update_or_create(
            slug="dvx-tedris-merkezi",
            defaults={
                "name": "DVX Tədris Mərkəzi",
                "address": "Bakı",  # TODO: şirkətdən dəqiq ünvan
                "phone": "+994502544969",
                "working_hours_text": "B.e-Cümə 09:00-18:00",  # TODO: dəqiqləşdir
                "instagram_page_id": opts["instagram_page_id"],
                "extra_info": (
                    "Vergi, mühasibatlıq və maliyyə sahəsində peşəkar təlimlər. "
                    "Təlimlər aylıq qruplarla keçirilir, yerlər məhduddur."
                ),
                "staff_label": "Təlimçilər",
                "guardrail_text": (
                    "Heç vaxt fərdi vergi, hüquq və ya maliyyə məsləhəti vermə — "
                    "konkret vergi hesablaması, bəyannamə doldurulması və ya "
                    "qanunvericiliyin şərhi soruşulsa, bildir ki, buna yalnız "
                    "mütəxəssis cavab verə bilər və operatora yönləndir. "
                    "İmtahan/sertifikat nəticəsinə və işə düzəlməyə zəmanət vermə."
                ),
                "is_active": True,
            },
        )

        business.services.all().delete()
        Service.objects.bulk_create(
            [
                Service(
                    business=business,
                    name="Vergi uçotu təlimi",
                    price_text="Qiymət (şirkətdən dəqiqləşdiriləcək)",
                ),
                Service(
                    business=business,
                    name="Mühasibatlıq təlimi",
                    price_text="Qiymət (şirkətdən dəqiqləşdiriləcək)",
                ),
            ]
        )

        business.staff_members.all().delete()
        StaffMember.objects.create(
            business=business,
            name="Təlimçi (nümunə)",
            specialty="Sahə (şirkətdən dəqiqləşdiriləcək)",
        )

        business.faq_items.all().delete()
        FAQItem.objects.bulk_create(
            [
                FAQItem(
                    business=business,
                    question="Növbəti təlim nə vaxt başlayır?",
                    answer="TODO: şirkətdən aylıq qrafik alınacaq.",
                ),
                FAQItem(
                    business=business,
                    question="Təlim online, yoxsa oflayn keçirilir?",
                    answer="TODO: şirkətdən dəqiqləşdiriləcək.",
                ),
                FAQItem(
                    business=business,
                    question="Sertifikat verilir?",
                    answer="TODO: şirkətdən dəqiqləşdiriləcək.",
                ),
            ]
        )

        user, _ = User.objects.get_or_create(
            username=opts["username"],
            defaults={"is_staff": True, "is_superuser": False},
        )
        user.set_password(opts["password"])
        user.is_staff = True
        user.save()
        BusinessMembership.objects.get_or_create(user=user, business=business)

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: '{business.name}' (instagram_page_id="
                f"{business.instagram_page_id or 'HƏLƏ YOXDUR — Faza B-də veriləcək'}); "
                f"operator: {opts['username']} / {opts['password']}\n"
                "DİQQƏT: qiymət/ünvan/FAQ PLACEHOLDER-dir — real məlumat "
                "alınandan sonra Django admin-dən doldur."
            )
        )
