"""Klinikanın bilik bazasından LLM sistem promptunun qurulması.

KB kiçik olduğu üçün vector DB istifadə olunmur — bütün məlumat
birbaşa sistem prompta yerləşdirilir (bax: dizayn sənədi).
"""


def build_system_prompt(clinic) -> str:
    sections = [_intro(clinic), _clinic_info(clinic)]

    services = clinic.services.filter(is_active=True)
    if services.exists():
        lines = []
        for s in services:
            line = f"- {s.name}"
            if s.price_text:
                line += f": {s.price_text}"
            if s.description:
                line += f" ({s.description})"
            lines.append(line)
        sections.append("## Xidmətlər və qiymətlər\n" + "\n".join(lines))

    doctors = clinic.doctors.filter(is_active=True)
    if doctors.exists():
        lines = []
        for d in doctors:
            line = f"- {d.name}"
            if d.specialty:
                line += f" — {d.specialty}"
            if d.info:
                line += f". {d.info}"
            lines.append(line)
        sections.append("## Həkimlər / Mütəxəssislər\n" + "\n".join(lines))

    faq_items = clinic.faq_items.filter(is_active=True)
    if faq_items.exists():
        lines = [f"S: {f.question}\nC: {f.answer}" for f in faq_items]
        sections.append("## Tez-tez verilən suallar\n" + "\n\n".join(lines))

    sections.append(_rules(clinic))
    return "\n\n".join(sections)


def _intro(clinic) -> str:
    return (
        f'Sən "{clinic.name}" adlı müəssisənin virtual müştəri köməkçisisən. '
        "Müştərilərlə Azərbaycan dilində, səmimi və peşəkar tonda danışırsan. "
        "Vəzifən: xidmətlər, qiymətlər, iş saatları və ünvan haqqında suallara "
        "aşağıdakı məlumat bazasına əsasən cavab vermək və randevu istəyən "
        "müştərilərin məlumatlarını toplamaqdır."
    )


def _clinic_info(clinic) -> str:
    lines = []
    if clinic.address:
        lines.append(f"Ünvan: {clinic.address}")
    if clinic.phone:
        lines.append(f"Telefon: {clinic.phone}")
    if clinic.working_hours_text:
        lines.append(f"İş saatları: {clinic.working_hours_text}")
    if clinic.extra_info:
        lines.append(clinic.extra_info)
    return "## Müəssisə haqqında\n" + "\n".join(lines)


def _rules(clinic) -> str:
    return (
        "## Qaydalar\n"
        "1. QƏTİ QAYDA: Heç vaxt tibbi məsləhət, diaqnoz və ya müalicə tövsiyəsi "
        "vermə. Müştəri simptom, ağrı, dərman və ya müalicə barədə soruşarsa, "
        'nəzakətlə bildir ki, bu suala yalnız həkim cavab verə bilər və '
        "konsultasiya üçün randevu təklif et.\n"
        "2. Yalnız yuxarıdakı məlumat bazasında olan faktları söylə. Bilmədiyin "
        "məlumatı uydurma — əvəzində operatora yönləndir.\n"
        "3. Müştəri randevu istəyəndə bu məlumatları topla: ad, əlaqə nömrəsi, "
        "istənilən xidmət, istənilən vaxt. Hamısı hazır olanda "
        "create_appointment_request alətini çağır.\n"
        "4. Müştəri insan operatorla danışmaq istəsə, sualı çətin/həssas olsa və ya "
        "narazılıq bildirsə, handoff_to_operator alətini çağır.\n"
        "5. Cavabları qısa və konkret saxla — bu, mesajlaşma söhbətidir.\n"
        "6. Həmişə Azərbaycan dilində cavab ver (müştəri başqa dildə yazsa, "
        "onun dilində cavab verə bilərsən)."
    )
