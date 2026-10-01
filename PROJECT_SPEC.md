# Proje Tanımı

## Amaç

Almanya odaklı iş ilanlarını yerel bir uygulamada toplamak, normalize etmek, tekrarları ayıklamak, aday profiline göre puanlamak ve başvuru sürecini Türkçe bir arayüzden takip etmeyi kolaylaştırmak.

Uygulama kişisel kullanım ve portföy amaçlıdır. Public repo kişisel veri, API anahtarı veya ilan veritabanı içermez.

## Kapsam

- Almanya öncelikli IT/yazılım ilanları
- Public API veya açık veri akışı olan kaynaklar
- Yerel SQLite veritabanı
- Türkçe kullanıcı arayüzü
- Aday profili ve CV içeriği düzenleme
- İlan bazlı CV ve ön yazı üretimi
- Opsiyonel Ollama desteği

## Kapsam Dışı

- Otomatik iş başvurusu
- CAPTCHA veya anti-bot aşma
- Giriş gerektiren ilan sitelerinden veri çekme
- Ücretli yapay zeka API’sine zorunlu bağımlılık
- Bulut veritabanı veya çok kullanıcılı SaaS yapı

## Hedef Roller

- Junior Software Developer
- Junior Frontend / Backend / Full Stack Developer
- IT Support
- System Administrator
- QA / Test Engineer
- Cybersecurity Analyst
- Application Support
- Junior IT Consultant

Arama terimleri Almanca ve İngilizce olarak tutulur.

## Kaynak Stratejisi

Kaynaklar üç gruptadır:

- Aktif kaynaklar: public API veya açık veri akışı olanlar
- API anahtarı isteyen kaynaklar: kullanıcı `.env` içine kendi anahtarını ekler
- Stub kaynaklar: güvenilir public erişim olmadığı için otomatik çekim yapılmaz

Uygulama bir kaynağın hata vermesi durumunda tüm yenileme sürecini durdurmaz.

## Veri Modeli

Temel ilan alanları:

- kaynak
- kaynak ilan kimliği
- başlık
- şirket
- konum
- açıklama
- ilan linki
- yayın tarihi
- ilk görülme tarihi
- son görülme tarihi
- çalışma modeli
- ilan dili
- Almanca/İngilizce gereksinimi
- deneyim seviyesi
- uygunluk puanı
- başvuru durumu

## Puanlama

Puanlama deterministik ve kural tabanlıdır.

Pozitif sinyaller:

- junior / entry-level ifadeleri
- hedef role uygunluk
- düşük deneyim beklentisi
- Almanca B1/B2 kabulü
- İngilizce kabulü
- remote veya hibrit çalışma
- ilgili eğitim/teknoloji sinyalleri

Negatif sinyaller:

- senior / lead / principal rol seviyesi
- yüksek deneyim gereksinimi
- zorunlu C1/C2 Almanca
- yönetim sorumluluğu
- hedef dışı rol

## Başvuru Durumları

- Yeni
- İnceleniyor
- Başvuruldu
- Mülakat
- Reddedildi
- Yoksayıldı
- Teklif

## Yapay Zeka Desteği

Ollama varsa:

- CV özeti
- uygunluk maddeleri
- ön yazı paragrafları

ilan içeriğine göre yerel olarak yeniden yazılabilir.

Ollama yoksa uygulama kural tabanlı üretime düşer.

## Gizlilik

Aşağıdaki dosyalar yalnızca yerelde kalır:

- `.env`
- `jobs.db`
- `candidate_profile.json`
- `cv_profile.json`
- `source_*.json`

Bu dosyalar public repo’ya eklenmemelidir.

## Hukuki ve Etik Sınırlar

- Resmi ortaklık iddia edilmez.
- Kaynakların kullanım şartlarına uyulmalıdır.
- Anti-bot/CAPTCHA aşma yapılmaz.
- Otomatik başvuru yapılmaz.
- Kullanıcı son başvuruyu resmi ilan sayfasında kendisi yapar.
