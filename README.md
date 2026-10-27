# MasterNR1 — AI müştəri köməkçisi (WhatsApp + Instagram)

Azərbaycan dilində işləyən AI müştəri köməkçisi. WhatsApp və Instagram DM-ə gələn
sorğulara bizneslərin bilik bazasından cavab verir, qeydiyyat/randevu sorğularını
toplayır və lazım olanda söhbəti canlı operatora ötürür.

## Əsas imkanlar
- **Multi-tenant:** hər biznes ayrıca tenant-dır; yeni müştəri əlavə etmək kod dəyişikliyi tələb etmir
- **Kanallar:** WhatsApp Cloud API və Instagram Messaging (Meta)
- **Bilik bazası:** qiymət, ünvan, FAQ — admin paneldən idarə olunur
- **Operator inbox:** AI-nin cavab verə bilmədiyi söhbətlər operatora ötürülür
- Real pilotlar: tədris mərkəzlərində (WhatsApp və Instagram)

## Texnologiyalar
Python · Django · Meta WhatsApp/Instagram API · LLM (Groq) · pytest/Django test (52 test)

## Quraşdırma
```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # açarları doldurun
python manage.py migrate
python manage.py runserver
```
Deploy təlimatı: [DEPLOY.md](DEPLOY.md)
