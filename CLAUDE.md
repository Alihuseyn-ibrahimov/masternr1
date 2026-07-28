# MasterNR1 — operativ təlimat

AZ-dilli AI müştəri köməkçisi: WhatsApp + Instagram DM-ə gələn sorğulara bilik
bazasından cavab verir, randevu/qeydiyyat sorğusu yığır, lazım olanda operatora
ötürür. Managed SaaS, multi-tenant.

**Dizayn sənədi:** `docs/superpowers/specs/2026-07-18-masternr1-assistant-design.md`
**Plan:** `.planning/2026-07-18-masternr1-mvp/task_plan.md`

## Vəziyyət

- Faza 1-4 **tamam**, 52/52 test keçir. Faza 5 (VPS deploy) qalır.
- Uçdan-uca canlı WhatsApp axını bir dəfə tam təsdiqlənib (Meta test nömrəsi ilə).
- **Aktiv pilot: Master NR 1 Tədris Mərkəzi** (magistratura/doktorantura/DQ hazırlıq).
  Təsisçidən razılıq var, görüş gözlənilir.
- Kod bir sahəyə bağlı deyil — `Business` modeli istənilən müəssisə üçün tenant-dır.
  Sistem multi-tenant qalır: gələcəkdə ikinci müştəri əlavə etmək kod dəyişikliyi
  tələb etmir, yalnız yeni `Business` yazısı + kanal ID-si lazımdır.

## Əmrlər

Bash tool-un cari qovluğu qorunmadığı üçün tam yol işlət:

```bash
P="C:/Users/Alihuseyn Ibrahimov/PycharmProjects/Quantum/masternr1"

"$P/.venv/Scripts/python" "$P/manage.py" test          # 52 test
"$P/.venv/Scripts/python" "$P/manage.py" migrate
"$P/.venv/Scripts/python" "$P/manage.py" makemigrations
"$P/.venv/Scripts/python" "$P/manage.py" runserver 8055

# Azərbaycan hərfləri çap edən əmrlərdə:
PYTHONIOENCODING=utf-8 "$P/.venv/Scripts/python" "$P/manage.py" seed_masternr1
```

**Seed komandası** (yalnız lokal test, `DEPLOY.md`-yə daxil deyil):
- `seed_masternr1` — Master NR 1 tenant-ı (operator: `masternr1` / `demopass123`).
  Qiymət/ünvan/FAQ sahələri PLACEHOLDER-dir — görüşdən sonra admin-dən doldurulur.

## Struktur

| App | Məsuliyyət |
|---|---|
| `businesses` | Tenant (`Business`) + bilik bazası: `Service`, `StaffMember`, `FAQItem` |
| `channels` | Meta webhook (GET verify + POST), imza yoxlanışı, dedup, göndərmə, Celery task |
| `assistant` | `Conversation`, `Message`, `CustomerRequest`; sistem promptu; Groq tool-use agenti; Telegram bildirişləri |
| `inbox` | Operator paneli: danışıqlar, cavab yazma, bot pauzası, sorğular siyahısı |

Əsas fayllar: `assistant/responder.py` (agent), `assistant/prompt.py` (sistem promptu),
`channels/tasks.py` (marşrutlaşdırma), `channels/parsing.py` (payload normalizasiyası).

## Multi-tenant marşrutlaşdırma — diqqət

Gələn mesaj `whatsapp_phone_number_id` / `instagram_page_id` ilə müəssisəyə bağlanır.
**Bir `phone_number_id` yalnız BİR müəssisədə ola bilər** — eyni ID iki tenant-a
yazılsa marşrutlaşdırma pozulur. Yeni tenant seed edəndə köhnəsinin ID-sini boşalt
(`seed_masternr1` bunu özü edir).

## Prompt fərdiləşdirmə (yeni müəssisə üçün)

Kod dəyişmədən `Business` sahələri ilə idarə olunur:

- `staff_label` — komanda bölməsinin başlığı (defolt "Komanda"; kursda
  "Repetitorlar / Müəllimlər")
- `guardrail_text` — **qəti qadağa qaydası**. Boş qalsa ümumi ehtiyatlı defolt
  işləyir (səlahiyyətdən kənar peşəkar məsləhət vermə + zəmanət vermə).
  Kursda: qəbul/nəticə zəmanəti verməmək.

Guardrail hər tenant üçün mütləqdir — hüquqi risk buradadır.

## Agent davranışı

İki alət var: `create_customer_request` (ad+telefon mütləq) və
`handoff_to_operator` (botu pauza edir). Alət çağırılmasa — adi mətn cavabı.
LLM xətası → `FALLBACK_REPLY` + Telegram alert. Tarixçə: son 20 mesaj.

Testlərdə `FakeClient` işlədilir (OpenAI/Groq formatında) — real API çağırılmır.

## LLM provayderi — həll olunmamış məsələ

Hazırda **Groq** (OpenAI-uyğun API). Model `ASSISTANT_MODEL` env ilə seçilir.

- `llama-3.3-70b-versatile` — keyfiyyət yaxşı, **pulsuz tier günlük 100K token**
  (bir danışıq ~2.6K token, tez tükənir)
- `llama-3.1-8b-instant` — kvotası böyük, **amma alət çağırışlarını korlayır**
  (JSON əvəzinə psevdo-XML üretir → `400 tool_use_failed`). Pilot üçün YARARSIZ.

**Canlı demodan əvvəl model qərarı verilməlidir** (Groq Dev Tier ödənişli və ya
Claude). Kod interfeysi provayderdən asılı deyil — dəyişiklik `_get_client` və
`_run_agent` daxilində məhdudlaşır. Qərarı istifadəçi verir, özün keçirmə.

## Meta inteqrasiyası — real tələlər

Bunlar canlı testdə baş verib, təkrarlanmasın:

1. **Access token 24 saatlıqdır.** Bitəndə göndərmə 401 verir. Yeniləyəndən sonra
   `.env`-i düzəlt **və Django serverini restart et** (env proses başlanğıcında oxunur).
2. **WABA ayrıca abunə tələb edir.** Meta panelində webhook subscribe etmək kifayət
   deyil — `POST /{waba_id}/subscribed_apps` ilə WABA bizim app-a abunə olmalıdır.
   Defolt olaraq başqa app-a abunə ola bilər, o zaman mesaj ümumiyyətlə gəlmir.
3. **cloudflared tunnel URL-i hər restartda dəyişir.** Dəyişəndə İKİ yeri yenilə:
   Meta-dakı Callback URL (+ Verify and save) və `.env`-dəki `DJANGO_ALLOWED_HOSTS`.
   Meta-dan verify GET gəlməyibsə, Callback URL köhnədir.
4. Test nömrəsi `v25.0` işlədir (`META_GRAPH_API_VERSION`).

## Konfiqurasiya

`.env` (gitignored, **commit etmə**) — nümunə üçün `.env.example`-a bax.
Açarlar: `GROQ_API_KEY`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_ACCESS_TOKEN`,
`META_GRAPH_API_VERSION`, `ASSISTANT_MODEL`, `TELEGRAM_BOT_TOKEN`,
`DJANGO_ALLOWED_HOSTS`, `CELERY_TASK_ALWAYS_EAGER`.

Dev-də Celery eager rejimdədir (Redis lazım deyil), baza SQLite.
Prod-da PostgreSQL keçidi (`dj-database-url`) hələ edilməyib — Faza 5 işidir.

## Yoxlama qaydası

Canlı test edəndə nəticəni **mesaj mətninə görə qiymətləndirmə**. Fallback mesajı
uğurlu cavaba oxşaya bilər. Həmişə yoxla:
- DB-də `Message` / `CustomerRequest` yazıları
- `Conversation.bot_paused` vəziyyəti
- server logları (`tool_use_failed`, `rate_limit_exceeded` kimi xətalar)
