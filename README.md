# Almanya İş Bul

Almanya odaklı, yerel çalışan ve yapay zeka destekli iş ilanı takip uygulaması.

Bu proje; Almanya’daki IT ve yazılım odaklı ilanları farklı açık kaynaklardan toplar, ilanları normalize eder, tekrarları ayıklar, aday profiline göre puanlar ve başvuru sürecini tek panelden takip etmeyi kolaylaştırır.

Uygulama kişisel verileri GitHub’a koymadan çalışacak şekilde tasarlanmıştır. CV/profil dosyaları, API anahtarları, kaynak önbellekleri ve SQLite veritabanı kullanıcının kendi makinesinde oluşur ve Git tarafından yok sayılır.

## Özellikler

- Almanya odaklı çok kaynaklı ilan yenileme
- Yerel SQLite veritabanı
- İlan normalizasyonu ve tekrar kayıt engelleme
- Aday profiline göre kural tabanlı uygunluk puanı
- Türkçe arayüz
- İlan filtreleme, detay görüntüleme ve başvuru durumu takibi
- İlan linkini açıp durumu başvuruldu olarak işaretleme
- Aday profili ve CV içeriği düzenleme
- İlan bazlı A4 Word CV ve ön yazı oluşturma
- Opsiyonel yerel yapay zeka desteği: Ollama
- Ollama kapalıysa kural tabanlı güvenli fallback

## Ekranlar

- Özet
- İlanlar
- Başvurular
- Profil

## Teknolojiler

| Katman | Teknoloji |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Frontend | React, Vite, TypeScript, Tailwind CSS |
| Belge üretimi | `python-docx` |
| Çeviri | `deep-translator` |
| Yerel yapay zeka | Ollama HTTP API |

## Mimari

```text
İlan Kaynakları
      ↓
Normalize Etme
      ↓
Rol Sınıflandırma
      ↓
Profil Bazlı Puanlama
      ↓
Tekrar Kayıt Kontrolü
      ↓
SQLite
      ↓
FastAPI
      ↓
React Arayüz
```

## İlan Kaynakları

| Kaynak | Durum | Not |
|---|---|---|
| Arbeitsagentur | Aktif | Public Jobsuche REST API |
| Arbeitnow | Aktif | Public job-board API |
| Absolventa | Aktif | Sitemap + JobPosting JSON-LD |
| EURES | Aktif | Public JSON search API |
| Jobicy | Aktif | Remote/IT ilan akışı |
| Remotive | Aktif | Remote ilan akışı |
| Jooble | API anahtarı varsa aktif | `JOOBLE_API_KEY` gerekir |
| Make it in Germany | Stub | Ayrı public API bulunmuyor |
| Jobvector | Stub | Partner/Cloudflare korumalı |
| GermanTechJobs | Stub | Public API deprecated |
| Glassdoor | Stub | Manuel link yönlendirme |

Bu proje korumalı sayfaları agresif şekilde kazımaz, CAPTCHA aşmaya çalışmaz ve otomatik başvuru yapmaz.

## Kurulum

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API dokümantasyonu:

```text
http://127.0.0.1:8000/docs
```

### Frontend

Başka bir terminal açın:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Arayüz:

```text
http://127.0.0.1:5173
```

## İlanları Yenileme

Arayüzde **İlanları Güncelle** butonuna basabilirsiniz.

Terminalden:

```bash
curl -X POST http://127.0.0.1:8000/jobs/refresh
```

İlk çalıştırmada veritabanı boş olabilir. İlanlar yenilendikten sonra `backend/data/jobs.db` dosyası yerel olarak oluşur.

## Opsiyonel Yerel Yapay Zeka

Uygulama Ollama çalışıyorsa CV özeti, uygunluk maddeleri ve ön yazı metnini ilana göre yerel olarak yeniden yazabilir.

```bash
ollama pull llama3.2:3b
ollama serve
```

`backend/.env` içinde:

```env
OLLAMA_ENABLED=true
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

Yapay zeka desteğini kapatmak için:

```env
OLLAMA_ENABLED=false
```

Ollama kapalıysa uygulama çalışmaya devam eder ve kural tabanlı CV/ön yazı üretimini kullanır.

## Ortam Değişkenleri

| Değişken | Amaç |
|---|---|
| `JOOBLE_API_KEY` | Jooble kaynağını etkinleştirir |
| `JOOBLE_MARKETS` | Varsayılan: `DE` |
| `OLLAMA_ENABLED` | Yerel yapay zeka desteğini açar/kapatır |
| `OLLAMA_HOST` | Varsayılan: `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Varsayılan: `llama3.2:3b` |
| `ARBEITSAGENTUR_*` | Arbeitsagentur istek limitleri ve zaman aşımı ayarları |
| `ARBEITNOW_*` | Arbeitnow limitleri |
| `ABSOLVENTA_*` | Absolventa limitleri |
| `EURES_*` | EURES limitleri |

## Yerel Dosyalar ve Gizlilik

Bu dosyalar GitHub’a gönderilmemelidir ve `.gitignore` içindedir:

- `backend/.env`
- `backend/data/jobs.db`
- `backend/data/candidate_profile.json`
- `backend/data/cv_profile.json`
- `backend/data/source_*.json`

Public repo kişisel CV, profil, API anahtarı veya iş ilanı veritabanı içermez.

## Hukuki ve Etik Not

Bu proje bağımsız, açık kaynaklı ve yerel çalışan bir yardımcı araçtır.

- Listelenen iş platformları, kurumlar veya veri sağlayıcılarla resmi bir ortaklık iddia etmez.
- İlan kaynaklarının kendi kullanım şartlarına uyulması kullanıcının sorumluluğundadır.
- Public API veya kullanıcı tarafından sağlanan API anahtarları kullanılır.
- Korumalı sayfalar, CAPTCHA, Cloudflare veya giriş gerektiren içerikler aşılmaya çalışılmaz.
- Otomatik iş başvurusu yapılmaz.
- İlanlar kullanıcı tarafından manuel kontrol edilmeli ve başvurular ilgili resmi ilan sayfası üzerinden yapılmalıdır.

## Proje Yapısı

```text
.
├── README.md
├── PROJECT_SPEC.md
├── TASKS.md
├── backend
│   ├── app
│   │   ├── api
│   │   ├── config
│   │   ├── db
│   │   ├── models
│   │   ├── schemas
│   │   ├── services
│   │   └── sources
│   ├── data
│   ├── tests
│   └── requirements.txt
└── frontend
    └── src
        ├── components
        ├── lib
        ├── services
        └── types
```

## Yol Haritası

- Tek komutla başlatma script’i
- Ekran görüntüleri ve kısa demo videosu
- Daha iyi hata mesajları
- Kaynak bazlı rate-limit ayarlarının arayüzden yönetimi
- Tauri ile masaüstü uygulama paketleme
- Daha kapsamlı test dokümantasyonu

## Lisans

Bu proje için MIT lisansı önerilir. Veri kaynaklarının kullanım şartları ayrıca geçerlidir.
