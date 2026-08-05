# Sentimen KPwBI Bali

Platform analisis sentimen publik untuk memantau percakapan di media sosial dan berita online terkait **Bank Indonesia Kantor Perwakilan Provinsi Bali (KPwBI Bali)**.

## Stack

| Layer | Teknologi |
|-------|-----------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, SQLAlchemy, APScheduler |
| Database | SQLite (local) / PostgreSQL (production) |
| Sentiment | LLM API (OpenAI/Anthropic) + leksikon InSet (fallback) |

## Struktur

```
frontend/          # Next.js dashboard
backend/           # FastAPI + connectors + sentiment engine
.env.example       # Template kredensial
```

## Setup Cepat

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # atau sesuaikan backend/.env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
# pastikan .env.local berisi NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Buka: http://localhost:3000

### 3. Data pertama

Dari halaman **Sumber Data** atau via API:

```bash
# Generate ~180 post sintetis + analisis leksikon
curl -X POST http://localhost:8000/ingest/seed?count=180

# Tarik berita Google News RSS berdasarkan keyword
curl -X POST http://localhost:8000/ingest/news

# Upload CSV/Excel (kolom wajib: text_raw, source)
curl -X POST http://localhost:8000/ingest/upload -F "file=@sample.csv"
```

## Fase Implementasi

1. **Fondasi** — schema DB, upload CSV/Excel, scraper berita RSS, dummy data
2. **Mesin sentimen** — `POST /analyze`, background job, cache hash teks
3. **Dashboard UI** — ringkasan, tren, platform, word cloud, topik, tabel + drill-down
4. **Connector medsos** — interface modular di `backend/app/connectors/` (X, Instagram, TikTok) + scheduler

## Endpoint Utama

| Method | Path | Keterangan |
|--------|------|------------|
| GET | `/health` | Health check |
| POST | `/analyze` | Analisis teks → JSON sentimen |
| GET | `/dashboard/overview` | Agregasi dashboard |
| GET | `/posts` | Daftar post + filter |
| GET | `/posts/{id}` | Detail post |
| GET | `/sources` | Status connector |
| POST | `/sources/{id}/sync` | Sinkronisasi connector |
| POST | `/ingest/upload` | Upload CSV/Excel |
| POST | `/ingest/news` | Tarik berita |
| POST | `/ingest/seed` | Dummy data |
| POST | `/ingest/analyze-pending` | Analisis post baru |

## Konfigurasi LLM

Di `backend/.env`:

```env
LLM_PROVIDER=openai          # openai | anthropic | none
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
# atau
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Jika `LLM_PROVIDER=none` atau API key kosong, sistem memakai leksikon InSet.

## Keyword Awal

Bank Indonesia Bali, BI Bali, KPwBI Bali, Achris Sarwani, Erwin Soeriadimadja,
rupiah Bali, penukaran uang Bali, QRIS Bali, inflasi Bali, SERAMBI Bank Indonesia,
Baligivation, Bali Investment Challenge, Panca Kerti Bali, UMKM ekspor Bali,
sistem pembayaran Bali, kurs Bali, KUPVA Bali, ekonomi Bali pariwisata, dll.

## Deployment

**Cloud (direkomendasikan):** Frontend → **Vercel**, Backend + Postgres → **Railway**  
→ panduan langkah demi langkah: [DEPLOY-VERCEL-RAILWAY.md](./DEPLOY-VERCEL-RAILWAY.md)

Alternatif Docker / VPS: [DEPLOY.md](./DEPLOY.md)

## Instagram Hashtag Search

Katalog ~98 hashtag (branding BI, ekonomi Bali, QRIS, UMKM, komunitas, edukasi) tersimpan di tabel `keywords` (kategori `ig_*`).

1. Buka **Sumber Data** → seed katalog / lihat daftar hashtag
2. **Demo** (tanpa API): `POST /ingest/instagram-demo` — post sintetis per hashtag prioritas
3. **Data asli**: isi di `backend/.env`:
   ```env
   INSTAGRAM_ACCESS_TOKEN=...
   INSTAGRAM_BUSINESS_ACCOUNT_ID=...
   INSTAGRAM_HASHTAG_SYNC_LIMIT=15
   ```
   lalu `POST /sources/instagram/sync`

Catatan: Graph API membatasi ~30 unique hashtag lookup per 7 hari; sync memakai daftar prioritas (`#BIBali`, `#QRISBali`, `#InflasiBali`, dll.).

## TikTok Research API

1. Daftarkan aplikasi di [TikTok for Developers](https://developers.tiktok.com/) dan ajukan akses **Research API** (tidak semua akun disetujui).
2. Isi di `backend/.env`:
   ```env
   TIKTOK_CLIENT_KEY=your_client_key
   TIKTOK_CLIENT_SECRET=your_client_secret
   TIKTOK_LOOKBACK_DAYS=30
   ```
3. Sync dari **Sumber Data** atau `POST /sources/tiktok/sync`
4. Caption masuk tabel `posts` (source=`tiktok`), lalu dianalisis oleh pipeline sentimen platform (LLM/InSet) — bukan skrip VADER terpisah.

Query default: keyword BI Bali / QRIS Bali + hashtag `bibali`, `qrisbali`, dll., region `ID`.
