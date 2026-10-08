# Deploy: Vercel (frontend) + Render (backend) — tanpa Railway

## Ringkasan

| Bagian | Platform | Folder |
|--------|----------|--------|
| Frontend Next.js | [Vercel](https://vercel.com) | `frontend/` |
| API FastAPI | [Render](https://render.com) | `backend/` |

Frontend sudah live: https://bi-bali-sentiment.vercel.app

---

## 1) Backend di Render (gratis)

### Via Blueprint (paling cepat)

1. Buka https://dashboard.render.com dan login (boleh pakai GitHub).
2. **Blueprints** → **New Blueprint Instance**.
3. Connect repo `efrizalthareq1/bi-bali-sentiment` (branch `main`).
4. Render membaca `render.yaml` di root → buat service `bi-aceh-sentiment-api`.
5. Deploy → salin URL publik, contoh:  
   `https://bi-aceh-sentiment-api.onrender.com`
6. Cek health: `https://URL_ANDA/health` → `{"status":"ok","service":"bi-aceh-sentiment"}`

### Via dashboard manual

1. **New** → **Web Service** → pilih repo yang sama.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Docker (pakai `backend/Dockerfile`)
   - **Instance type:** Free
3. Environment:

| Variable | Nilai |
|----------|--------|
| `CORS_ORIGINS` | `https://bi-bali-sentiment.vercel.app` |
| `ENABLE_SCHEDULER` | `true` |
| `LLM_PROVIDER` | `none` |
| `DATABASE_URL` | `sqlite:///./data/sentiment.db` |

4. Deploy → salin URL.

> Free tier Render tidur setelah ~15 menit idle. Request pertama bisa 30–60 detik (cold start). Itu normal, bukan error permanen.

---

## 2) Hubungkan Vercel ke API Render

Di Vercel project `bi-bali-sentiment` → **Settings → Environment Variables**:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://URL_RENDER_ANDA` *(tanpa slash akhir)* |

Lalu **Redeploy** Production (nilai `NEXT_PUBLIC_*` di-bake saat build).

Via CLI:

```powershell
cd C:\Users\user\Projects\pdrb-bali-dashboard\frontend
npx vercel env rm NEXT_PUBLIC_API_URL production -y
npx vercel env add NEXT_PUBLIC_API_URL production
# paste URL Render saat diminta
npx vercel --prod
```

---

## 3) Seed data pertama

Setelah `/health` OK:

```powershell
Invoke-RestMethod -Method POST "https://URL_RENDER_ANDA/ingest/seed?count=100"
Invoke-RestMethod -Method POST "https://URL_RENDER_ANDA/ingest/news"
```

Atau dari UI Vercel → **Sumber Data** → sinkronkan.

---

## Alternatif lain (tanpa Railway)

| Platform | File / catatan |
|----------|----------------|
| **Fly.io** | `backend/fly.toml` — `cd backend; fly launch; fly secrets set CORS_ORIGINS=...` |
| **Neon Postgres** | Gratis; ganti `DATABASE_URL` di Render/Fly ke connection string Neon |

---

## Checklist

- [ ] Render `/health` OK
- [ ] Vercel `NEXT_PUBLIC_API_URL` = URL Render
- [ ] `CORS_ORIGINS` = `https://bi-bali-sentiment.vercel.app`
- [ ] Redeploy Vercel setelah ubah env
- [ ] Seed / sync data

## Troubleshooting

| Masalah | Perbaikan |
|---------|-----------|
| Failed to fetch / timeout pertama | Tunggu cold start Render, refresh sekali lagi |
| CORS error | Samakan `CORS_ORIGINS` dengan origin Vercel |
| Data hilang setelah redeploy | SQLite ephemeral — pakai Neon Postgres gratis |
| Dashboard masih URL Railway lama | Update `NEXT_PUBLIC_API_URL` + redeploy Vercel |
