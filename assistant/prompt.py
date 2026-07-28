"""Müəssisənin bilik bazasından LLM sistem promptunun qurulması.

KB kiçik olduğu üçün vector DB istifadə olunmur — bütün məlumat
birbaşa sistem prompta yerləşdirilir (bax: dizayn sənədi).
"""


def build_system_prompt(business) -> str:
    sections = [_intro(business), _business_info(business)]

    services = business.services.filter(is_active=True)
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

    staff_members = business.staff_members.filter(is_active=True)
    if staff_members.exists():
        lines = []
        for d in staff_members:
            line = f"- {d.name}"
            if d.specialty:
                line += f" — {d.specialty}"
            if d.info:
                line += f". {d.info}"
            lines.append(line)
        sections.append(f"## {business.staff_label}\n" + "\n".join(lines))

    faq_items = business.faq_items.filter(is_active=True)
    if faq_items.exists():
        lines = [f"S: {f.question}\nC: {f.answer}" for f in faq_items]
        sections.append("## Tez-tez verilən suallar\n" + "\n\n".join(lines))

    sections.append(_rules(business))
    return "\n\n".join(sections)


def _intro(business) -> str:
    return (
        f'Sən "{business.name}" adlı müəssisənin virtual müştəri köməkçisisən. '
        "Müştərilərlə Azərbaycan dilində, səmimi və peşəkar tonda danışırsan. "
        "Vəzifən: xidmətlər/proqramlar, qiymətlər, iş saatları və ünvan haqqında "
        "suallara aşağıdakı məlumat bazasına əsasən cavab vermək və randevu/"
        "qeydiyyat istəyən müştərilərin məlumatlarını toplamaqdır."
    )


def _business_info(business) -> str:
    lines = []
    if business.address:
        lines.append(f"Ünvan: {business.address}")
    if business.phone:
        lines.append(f"Telefon: {business.phone}")
    if business.working_hours_text:
        lines.append(f"İş saatları: {business.working_hours_text}")
    if business.extra_info:
        lines.append(business.extra_info)
    return "## Müəssisə haqqında\n" + "\n".join(lines)


def _rules(business) -> str:
    guardrail = business.guardrail_text.strip() or (
        "Müəssisənin səlahiyyətindən kənar peşəkar məsləhət (tibbi, hüquqi, "
        "maliyyə) vermə və heç bir nəticəyə zəmanət vermə. Belə sual gələrsə, "
        "nəzakətlə bildir ki, buna yalnız mütəxəssis cavab verə bilər və "
        "operatora yönləndir."
    )
    return (
        "## Qaydalar\n"
        f"1. QƏTİ QAYDA: {guardrail}\n"
        "2. Yalnız yuxarıdakı məlumat bazasında olan faktları söylə. Bilmədiyin "
        "məlumatı uydurma — əvəzində operatora yönləndir.\n"
        "3. Müştəri randevu/qeydiyyat istəyəndə bu məlumatları topla: ad, əlaqə "
        "nömrəsi, istənilən xidmət/proqram, istənilən vaxt. Hamısı hazır olanda "
        "create_customer_request alətini çağır.\n"
        "4. Müştəri insan operatorla danışmaq istəsə, sualı çətin/həssas olsa və ya "
        "narazılıq bildirsə, handoff_to_operator alətini çağır.\n"
        "5. Cavabları qısa və konkret saxla — bu, mesajlaşma söhbətidir.\n"
        "6. Həmişə Azərbaycan dilində cavab ver (müştəri başqa dildə yazsa, "
        "onun dilində cavab verə bilərsən)."
    )
