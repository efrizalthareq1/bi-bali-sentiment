# Panduan Deploy — Sentimen KPwBI Bali

Stack: **Next.js (frontend)** + **FastAPI (backend)** + **SQLite/PostgreSQL**.

Cara paling cepat untuk production: **Docker Compose** (lokal atau VPS).

---

## Opsi A — Docker Compose (direkomendasikan)

### Prasyarat
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) terpasang dan berjalan

### Langkah

1. Siapkan env production:
   ```powershell
   copy .env.production.example .env.production
   ```

2. Edit `.env.production`:
   - **Lokal:** biarkan `localhost` seperti contoh
   - **VPS:** ganti ke IP/domain publik, contoh:
     ```env
     NEXT_PUBLIC_API_URL=http://IP_VPS_ANDA:8000
     CORS_ORIGINS=http://IP_VPS_ANDA:3000
     ```

3. Build & jalankan:
   ```powershell
   docker compose up -d --build
   ```

4. Buka:
   - Web: http://localhost:3000 (atau `http://IP_VPS:3000`)
   - API docs: http://localhost:8000/docs

5. Seed data awal (opsional):
   ```powershell
   curl -X POST http://localhost:8000/ingest/seed?count=100
   curl -X POST http://localhost:8000/ingest/news
   ```

### Perintah berguna
```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
```

Data SQLite tersimpan di volume Docker `backend_data`.

---

## Opsi B — Cloud terpisah (Vercel + Railway/Render)

| Bagian | Platform | Catatan |
|--------|----------|---------|
| Frontend | Vercel | Root directory = `frontend`, set `NEXT_PUBLIC_API_URL` ke URL backend |
| Backend | Railway / Render | Root = `backend`, start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Database | Postgres managed | Set `DATABASE_URL=postgresql://...` |
| CORS | Backend env | `CORS_ORIGINS=https://your-frontend.vercel.app` |

Pastikan `NEXT_PUBLIC_API_URL` di Vercel mengarah ke URL publik backend (bukan `localhost`).

---

## Opsi C — Manual di VPS (tanpa Docker)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
# isi .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm ci
# set NEXT_PUBLIC_API_URL di .env.local / .env.production
npm run build
npm run start -- -H 0.0.0.0 -p 3000
```

Disarankan pakai **nginx** + **systemd** (atau PM2) agar proses auto-restart.

---

## Checklist production

- [ ] `CORS_ORIGINS` memuat URL frontend publik
- [ ] `NEXT_PUBLIC_API_URL` memuat URL backend publik (di-bake saat `next build`)
- [ ] Volume/DB persistent (jangan hilang saat restart)
- [ ] Firewall buka port 3000 & 8000 (atau 80/443 via nginx)
- [ ] (Opsional) HTTPS dengan Let's Encrypt
- [ ] (Opsional) isi `OPENAI_API_KEY` / connector tokens

---

## Troubleshooting

| Gejala | Penyebab umum | Perbaikan |
|--------|---------------|-----------|
| Browser `ERR_CONNECTION_REFUSED` | Container/proses belum jalan | `docker compose ps` / start ulang |
| Dashboard kosong / CORS error | `CORS_ORIGINS` salah | Samakan dengan URL frontend |
| Frontend memanggil API localhost di VPS | `NEXT_PUBLIC_API_URL` salah saat build | Set env lalu `docker compose up -d --build` ulang |
| Data hilang setelah restart | Volume tidak terpasang | Pastikan `backend_data` di compose |
