# MasterNR1 — Deploy və Pilot Onboarding Təlimatı

Bu sənəd Faza 5-i (canlı işə salma) icra etmək üçündür. Kod tam hazırdır;
qalan yalnız secret-lər, servis konfiqurasiyası və pilot müəssisənin məlumatlarıdır.

## 0. Ön şərtlər (səndən lazım olanlar)

| Nə | Haradan |
|----|---------|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_ACCESS_TOKEN` | developers.facebook.com app |
| WhatsApp `phone_number_id` | Meta app → WhatsApp → API Setup |
| Instagram `page_id` | Bağlı FB/IG səhifəsi |
| `TELEGRAM_BOT_TOKEN` + müəssisə qrup `chat_id` | @BotFather + qrupa bot əlavə et |
| VPS + HTTPS domen (məs. bot.prdostu.com subdomeni) | mövcud |

`META_VERIFY_TOKEN` özün seçdiyin ixtiyari sətirdir (webhook qeydiyyatında
Meta panelinə eyni dəyəri yazacaqsan).

## 1. Server hazırlığı

```bash
sudo apt install -y python3-venv redis-server postgresql
sudo -u postgres createdb masternr1
sudo -u postgres createuser masternr1 --pwprompt   # şifrə qeyd et
```

Kod deploy:

```bash
cd /opt && git clone <repo> quantum && cd quantum/masternr1
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install gunicorn psycopg2-binary
cp .env.example .env    # sonra .env-i doldur (aşağıya bax)
```

## 2. `.env` (prod)

```
DJANGO_SECRET_KEY=<uzun təsadüfi sətir>
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=bot.prdostu.com
DATABASE_URL=postgres://masternr1:<şifrə>@localhost/masternr1   # settings-ə əlavə lazımdır (aşağı qeyd)
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

`deploy/masternr1-web.service` və `deploy/masternr1-celery.service` fayllarını
`/etc/systemd/system/`-ə kopyala, sonra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now masternr1-web masternr1-celery
```

Nginx: `bot.prdostu.com` → `127.0.0.1:8060` reverse proxy + Certbot TLS.
**Meta webhook HTTPS tələb edir.**

## 4. Meta webhook qeydiyyatı

Meta app → WhatsApp/Instagram → Webhooks → Callback URL:
`https://bot.prdostu.com/webhook/meta/`, Verify Token: `.env`-dəki
`META_VERIFY_TOKEN`. `messages` sahəsinə abunə ol.

## 5. Pilot müəssisənin onboarding-i (Django admin)

`/admin/`-ə gir → **Businesses**:
1. Müəssisə yarat: ad, slug, ünvan, telefon, iş saatları, `whatsapp_phone_number_id`,
   `instagram_page_id`, `telegram_chat_id`.
2. İçəridə (inline): Xidmətlər/proqramlar (+qiymət), Komanda üzvləri, FAQ.
3. `staff_label` və **`guardrail_text`** sahələrini bu müəssisəyə uyğun doldur —
   guardrail boş buraxılmamalıdır (hüquqi risk).
4. **BusinessMembership**: operator user-i müəssisəyə bağla (panelə giriş üçün).

## 6. Yoxlama

- WhatsApp test nömrəsindən mesaj at → bot cavab verməli, `/inbox/`-da görünməli.
- Qeydiyyat istə → `CustomerRequest` yaranmalı + Telegram qrupa bildiriş.
- "Operatorla danışmaq istəyirəm" → bot pauza + Telegram bildiriş.
- Guardrail testi: zəmanət soruş (məs. "qəbul olacağıma zəmanət verirsiniz?") →
  bot zəmanət VERMƏMƏLİ, operatora yönləndirməli.
