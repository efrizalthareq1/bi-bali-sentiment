# Deploy: Vercel (frontend) + Railway (backend)

## Ringkasan

| Bagian | Platform | Folder |
|--------|----------|--------|
| Frontend Next.js | [Vercel](https://vercel.com) | `frontend/` |
| API FastAPI + Postgres | [Railway](https://railway.app) | `backend/` |

Urutan: **Railway dulu** (dapat URL API) → baru **Vercel** (butuh `NEXT_PUBLIC_API_URL`).

---

## 1) Backend di Railway

### Via dashboard (paling mudah)

1. Buat akun di https://railway.app dan login.
2. **New Project** → **Deploy from GitHub repo**  
   *(Kalau belum ada repo GitHub: push project ini dulu, atau pakai opsi CLI di bawah.)*
3. Set **Root Directory** = `backend`
4. **Add Plugin** → **PostgreSQL**
5. Di service API, buka **Variables** dan isi:

| Variable | Nilai |
|----------|--------|
| `DATABASE_URL` | *(otomatis dari plugin Postgres — pastikan ter-link)* |
| `CORS_ORIGINS` | `*` dulu, diganti URL Vercel setelah frontend live |
| `ENABLE_SCHEDULER` | `true` |
| `LLM_PROVIDER` | `none` (atau `openai` / `anthropic`) |
| `OPENAI_API_KEY` | opsional |
| `X_BEARER_TOKEN` | opsional |
| `INSTAGRAM_ACCESS_TOKEN` | opsional |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | opsional |
| `TIKTOK_CLIENT_KEY` | opsional |
| `TIKTOK_CLIENT_SECRET` | opsional |

6. **Settings → Networking → Generate Domain** → salin URL, contoh:  
   `https://bi-bali-api-production.up.railway.app`
7. Cek health: `https://URL_ANDA/health` harus `{"status":"ok",...}`

Start command (sudah di `backend/railway.toml`):

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Via CLI (tanpa GitHub)

```powershell
cd C:\Users\user\Projects\pdrb-bali-dashboard\backend
npx @railway/cli login
npx @railway/cli init
npx @railway/cli add --database postgres
npx @railway/cli up
npx @railway/cli domain
```

Lalu set variables lewat dashboard Railway.

---

## 2) Frontend di Vercel

1. Buat akun di https://vercel.com
2. **Add New Project** → import repo GitHub yang sama
3. Konfigurasi:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js
4. **Environment Variables:**

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://URL_RAILWAY_ANDA` *(tanpa slash di akhir)* |

5. Deploy → salin URL Vercel, contoh:  
   `https://pdrb-bali-dashboard.vercel.app`

### Via CLI

```powershell
cd C:\Users\user\Projects\pdrb-bali-dashboard\frontend
npx vercel login
npx vercel
# production:
npx vercel --prod
```

Saat diminta env, set `NEXT_PUBLIC_API_URL` ke URL Railway.

---

## 3) Kunci CORS setelah Vercel live

Di Railway → Variables, ganti:

```env
CORS_ORIGINS=https://your-app.vercel.app
```

(boleh koma-separated jika ada preview domain)

Redeploy backend (atau biarkan restart otomatis).

---

## 4) Seed data pertama

```powershell
curl -X POST "https://URL_RAILWAY_ANDA/ingest/seed?count=100"
curl -X POST "https://URL_RAILWAY_ANDA/ingest/news"
```

Atau dari UI **Sumber Data** di situs Vercel.

---

## Checklist

- [ ] Railway `/health` OK
- [ ] Postgres ter-link (`DATABASE_URL`)
- [ ] Vercel `NEXT_PUBLIC_API_URL` = URL Railway
- [ ] `CORS_ORIGINS` = URL Vercel
- [ ] Dashboard menampilkan data (bukan error jaringan)

## Troubleshooting

| Masalah | Perbaikan |
|---------|-----------|
| CORS error di browser | Samakan `CORS_ORIGINS` dengan origin Vercel (https, tanpa slash) |
| API 502 di Railway | Cek logs; pastikan start command pakai `$PORT` |
| Dashboard kosong | Seed data; cek Network tab apakah API URL benar |
| `NEXT_PUBLIC_*` tidak berubah | Redeploy Vercel setelah ubah env (nilai di-bake saat build) |
| SQLite / data hilang | Jangan pakai SQLite di Railway — wajib Postgres plugin |
