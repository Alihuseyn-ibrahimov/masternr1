# MasterNR1 — AI Customer Assistant for WhatsApp & Instagram

An AI customer assistant that answers customer messages on **WhatsApp** and **Instagram Direct** in Azerbaijani. It replies from each business's own knowledge base, collects registration and appointment requests, and hands the conversation to a human operator when needed.

## Key features
- **Multi-tenant SaaS** — every business is a separate tenant; onboarding a new client needs no code changes
- **Channels** — WhatsApp Cloud API and Instagram Messaging (Meta)
- **Knowledge base** — prices, locations and FAQs managed from the admin panel
- **Operator inbox** — conversations the AI cannot resolve are escalated to a human
- **Live pilots** with education centres (WhatsApp and Instagram)

## Tech stack
Python · Django · Meta WhatsApp / Instagram APIs · LLM (Groq, LangChain) · automated tests

## Getting started
```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys
python manage.py migrate
python manage.py runserver
```
Deployment guide: [DEPLOY.md](DEPLOY.md)

---

## Azərbaycan dilində

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
