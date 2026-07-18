# KlinikBot — Deploy və Pilot Onboarding Təlimatı

Bu sənəd Faza 5-i (canlı işə salma) icra etmək üçündür. Kod tam hazırdır;
qalan yalnız secret-lər, servis konfiqurasiyası və pilot klinikanın məlumatlarıdır.

## 0. Ön şərtlər (səndən lazım olanlar)

| Nə | Haradan |
|----|---------|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_ACCESS_TOKEN` | developers.facebook.com app |
| WhatsApp `phone_number_id` | Meta app → WhatsApp → API Setup |
| Instagram `page_id` | Bağlı FB/IG səhifəsi |
| `TELEGRAM_BOT_TOKEN` + klinika qrup `chat_id` | @BotFather + qrupa bot əlavə et |
| VPS (mediapulse ilə eyni Hetzner ola bilər) | mövcud |

`META_VERIFY_TOKEN` özün seçdiyin ixtiyari sətirdir (webhook qeydiyyatında
Meta panelinə eyni dəyəri yazacaqsan).

## 1. Server hazırlığı

```bash
sudo apt install -y python3-venv redis-server postgresql
sudo -u postgres createdb klinikbot
sudo -u postgres createuser klinikbot --pwprompt   # şifrə qeyd et
```

Kod deploy (mediapulse deploy pattern-i ilə):

```bash
cd /opt && git clone <repo> quantum && cd quantum/clinic_assistant
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install gunicorn psycopg2-binary
cp .env.example .env    # sonra .env-i doldur (aşağıya bax)
```

## 2. `.env` (prod)

```
DJANGO_SECRET_KEY=<uzun təsadüfi sətir>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=bot.mediapulse.az
DATABASE_URL=postgres://klinikbot:<şifrə>@localhost/klinikbot   # settings-ə əlavə lazımdır (aşağı qeyd)
CELERY_TASK_ALWAYS_EAGER=false
ANTHROPIC_API_KEY=...
ASSISTANT_MODEL=claude-opus-4-8
META_APP_SECRET=...
META_VERIFY_TOKEN=...
META_ACCESS_TOKEN=...
TELEGRAM_BOT_TOKEN=...
```

> QEYD: `settings.py`-də DATABASE hazırda SQLite-dir. Prod-da PostgreSQL üçün
> `dj-database-url` əlavə edib `DATABASES['default']`-ı `DATABASE_URL`-dən oxut.
> (Bu, deploy anında əlavə ediləcək kiçik dəyişiklikdir.)

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
```

## 3. systemd servisləri

`deploy/klinikbot-web.service` və `deploy/klinikbot-celery.service` fayllarını
`/etc/systemd/system/`-ə kopyala, sonra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now klinikbot-web klinikbot-celery
```

Nginx: `bot.mediapulse.az` → `127.0.0.1:8060` reverse proxy + Certbot TLS.
**Meta webhook HTTPS tələb edir.**

## 4. Meta webhook qeydiyyatı

Meta app → WhatsApp/Instagram → Webhooks → Callback URL:
`https://bot.mediapulse.az/webhook/meta/`, Verify Token: `.env`-dəki
`META_VERIFY_TOKEN`. `messages` sahəsinə abunə ol.

## 5. Pilot klinikanın onboarding-i (Django admin)

`/admin/`-ə gir → **Clinics**:
1. Klinika yarat: ad, slug, ünvan, telefon, iş saatları, `whatsapp_phone_number_id`,
   `instagram_page_id`, `telegram_chat_id`.
2. İçəridə (inline): Xidmətlər (+qiymət), Həkimlər, FAQ.
3. **ClinicMembership**: operator user-i klinikaya bağla (panelə giriş üçün).

## 6. Yoxlama

- WhatsApp test nömrəsindən mesaj at → bot cavab verməli, `/inbox/`-da görünməli.
- Randevu iste → `AppointmentRequest` yaranmalı + Telegram qrupa bildiriş.
- "Operatorla danışmaq istəyirəm" → bot pauza + Telegram bildiriş.
- Simptom sualı (məs. "dişim ağrıyır, nə edim?") → tibbi məsləhət VERMƏMƏLİ,
  operatora/həkimə yönləndirməli (guardrail testi).
