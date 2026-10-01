# Görevler ve Yol Haritası

Bu dosya public repo için sade geliştirme durumunu ve sonraki işleri takip eder.

## Tamamlananlar

- [x] FastAPI backend
- [x] React + Vite + TypeScript frontend
- [x] Türkçe arayüz
- [x] SQLite tabanlı yerel veri saklama
- [x] Çok kaynaklı ilan yenileme
- [x] İlan normalizasyonu
- [x] Tekrar ilan engelleme
- [x] Profil bazlı uygunluk puanı
- [x] İlan filtreleme
- [x] Başvuru durumu takibi
- [x] Kaynak durum paneli
- [x] Aday profili düzenleme
- [x] CV profili düzenleme
- [x] İlan bazlı Word CV oluşturma
- [x] İlan bazlı ön yazı oluşturma
- [x] Opsiyonel Ollama desteği
- [x] Public repo için kişisel verilerin temizlenmesi
- [x] Public repo için Türkçe README ve proje dokümanı

## Aktif İlan Kaynakları

- [x] Arbeitsagentur
- [x] Arbeitnow
- [x] Absolventa
- [x] EURES
- [x] Jobicy
- [x] Remotive
- [x] Jooble (`JOOBLE_API_KEY` varsa)

## Bilerek Otomatik Çekilmeyen Kaynaklar

- [x] Jobvector: partner/Cloudflare korumalı
- [x] Make it in Germany: ayrı public API yok
- [x] GermanTechJobs: public API deprecated
- [x] Glassdoor: public otomatik erişim yok

## Sıradaki Gerçek Geliştirme Fikirleri

- [ ] Tek komutla başlatma script’i (`start.sh`)
- [ ] Ekran görüntüleri ekleme
- [ ] Kısa demo GIF/video ekleme
- [ ] MIT lisansı ekleme
- [ ] GitHub Actions ile frontend build kontrolü
- [ ] Backend test komutu dokümantasyonu
- [ ] Kaynak bazlı daha anlaşılır hata mesajları
- [ ] Tauri masaüstü uygulama denemesi

## GitHub Workflow Notu

Yeni geliştirmeler doğrudan `main` üzerinde yapılmamalıdır.

Önerilen akış:

```text
task
→ branch
→ implement
→ test
→ commit
→ push
→ pull request
→ review/verify
→ merge
```

Branch örnekleri:

- `feat/...`
- `fix/...`
- `docs/...`
- `refactor/...`
- `test/...`
- `chore/...`

Boş commit, sahte issue, gereksiz PR veya yalnızca aktivite artırmaya yönelik işlem yapılmamalıdır.
