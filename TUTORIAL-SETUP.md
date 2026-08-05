# Tutorial: Membuka & Menjalankan Sentimen KPwBI Bali

Dokumen ini menjelaskan cara membuka file ZIP source code dan menjalankan dashboard secara lokal di komputer Windows.

**Nama aplikasi:** Sentimen KPwBI Bali  
**Isi ZIP:** source code frontend (Next.js) + backend (FastAPI)  
**Demo online (jika sudah di-deploy):** https://bi-bali-sentiment.vercel.app

---

## 1. Apa yang Ada di Dalam ZIP?

| Folder / File | Keterangan |
|---------------|------------|
| `frontend/` | Tampilan dashboard (Next.js, TypeScript) |
| `backend/` | API + analisis sentimen + konektor data (Python) |
| `.env.example` | Template pengaturan lingkungan |
| `README.md` | Ringkasan teknis proyek |
| `TUTORIAL-SETUP.md` | Dokumen ini |
| `DEPLOY.md` | Panduan deploy (opsional) |

**Catatan:** Folder `node_modules` dan virtual environment Python **tidak** disertakan di ZIP (ukuran besar). Keduanya akan dibuat otomatis saat instalasi di bawah.

---

## 2. Prasyarat (Install Sekali)

Pastikan komputer sudah terpasang:

1. **Python 3.11 atau 3.12**  
   Unduh: https://www.python.org/downloads/  
   Centang opsi **“Add python.exe to PATH”** saat install.

2. **Node.js 18 atau 20 (LTS)**  
   Unduh: https://nodejs.org/  
   Pilih versi LTS.

3. **Editor teks (opsional)**  
   Visual Studio Code: https://code.visualstudio.com/

Cek instalasi di PowerShell / Command Prompt:

```powershell
python --version
node --version
npm --version
```

---

## 3. Membuka File ZIP

1. Simpan file ZIP, misalnya:  
   `bi-bali-sentiment-source.zip`
2. Klik kanan → **Extract All…** / **Extract Here**
3. Hasil ekstraksi akan berupa folder, misalnya:  
   `pdrb-bali-dashboard` atau `bi-bali-sentiment-source`
4. Buka folder tersebut. Di dalamnya harus terlihat `frontend/` dan `backend/`.

---

## 4. Menjalankan Backend (API)

Buka **PowerShell**, lalu:

```powershell
cd PATH\KE\FOLDER\HASIL\EXTRACT\backend

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt
```

Buat file konfigurasi lokal:

```powershell
copy ..\.env.example .env
```

Edit `backend\.env` bila perlu. Untuk uji lokal, isi minimal:

```env
DATABASE_URL=sqlite:///./data/sentiment.db
LLM_PROVIDER=none
CORS_ORIGINS=http://localhost:3000
ENABLE_SCHEDULER=true
```

Jalankan server:

```powershell
uvicorn app.main:app --reload --port 8000
```

Jika berhasil:
- API: http://localhost:8000  
- Dokumentasi API: http://localhost:8000/docs  
- Health check: http://localhost:8000/health  

**Biarkan jendela PowerShell ini tetap terbuka** selama memakai dashboard.

---

## 5. Menjalankan Frontend (Dashboard)

Buka **PowerShell baru** (jangan tutup yang backend), lalu:

```powershell
cd PATH\KE\FOLDER\HASIL\EXTRACT\frontend

npm install
```

Buat file `frontend\.env.local` berisi:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Jalankan:

```powershell
npm run dev
```

Buka browser: **http://localhost:3000**

---

## 6. Cara Menggunakan Dashboard

### Menu utama
- **Beranda** — halaman pengantar
- **Dashboard** — ringkasan sentimen, grafik, tabel, SNA Graph
- **Sumber Data** — status konektor & tombol sync data

### Filter Global (di Dashboard)
- **Platform** — X, Instagram, TikTok, Berita, YouTube, Threads, dll.
- **Sentimen** — Positif / Negatif / Netral
- **Keyword** — cari topik (mis. GPIPS, inflasi, QRIS)
- **Tanggal** — rentang waktu
- **Cari teks** — pencarian bebas di isi postingan

### Tombol di Dashboard
- **Muat ulang** — refresh data dari backend
- **Generate Dummy Data** — buat data contoh untuk demo (berguna jika DB masih kosong)

### Sumber Data
1. Buka menu **Sumber Data**
2. Untuk berita online: klik sync pada konektor **Berita**
3. Untuk YouTube / X / Threads: sync bila konektor berstatus siap
4. Upload CSV/Excel bila ada data internal (kolom wajib: `text_raw`, `source`)

### Membaca hasil sentimen
- **Positif** — nada mendukung / apresiatif
- **Negatif** — nada kritik / keluhan
- **Netral** — informatif tanpa nada kuat
- Skor InSet (jika dipakai) mendekati analisis berbasis leksikon bahasa Indonesia

### SNA Graph
Panel **SNA by Sentiment** menampilkan jaringan keyword, akun/outlet, dan topik yang diwarnai menurut klaster sentimen.

---

## 7. Alur Kerja yang Disarankan untuk Demo ke Atasan

1. Jalankan backend + frontend (bagian 4–5)
2. Buka http://localhost:3000/dashboard
3. Klik **Generate Dummy Data** (jika belum ada data)
4. Atau sync **Berita** dari **Sumber Data** untuk data nyata
5. Tunjukkan ringkasan %, tren, platform, word cloud, tabel, dan SNA Graph
6. Filter keyword misalnya `Bank Indonesia`, `inflasi`, `QRIS`, `GPIPS`

---

## 8. Versi Online (Tanpa Install)

Jika hanya ingin melihat hasil tanpa menjalankan ZIP:

- Frontend: https://bi-bali-sentiment.vercel.app  
- Backend API: https://api-production-58a9.up.railway.app  

ZIP tetap berguna untuk audit kode, pengembangan lanjut, atau instalasi di komputer internal.

---

## 9. Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `python` tidak dikenali | Install ulang Python + centang PATH, lalu buka ulang PowerShell |
| `npm` tidak dikenali | Install Node.js LTS, lalu buka ulang PowerShell |
| Dashboard error / “backend tidak berjalan” | Pastikan backend di port 8000 masih aktif; cek http://localhost:8000/health |
| Port 8000 sudah dipakai | Hentikan proses lama, atau jalankan uvicorn di port lain + sesuaikan `.env.local` |
| `pip install` gagal | Pastikan venv aktif (`.\.venv\Scripts\activate`) |
| `npm install` lama / gagal | Pastikan koneksi internet stabil; coba ulang |
| Halaman kosong setelah sync | Klik **Muat ulang** di Dashboard |

---

## 10. Keamanan & Catatan untuk Sharing

- Jangan menyertakan file `.env` / `.env.local` yang berisi API key asli saat ZIP dishare.
- ZIP resmi sudah dikemas **tanpa** kredensial rahasia.
- Untuk production, gunakan PostgreSQL + environment variables di hosting (lihat `DEPLOY.md`).

---

## Kontak Teknis Singkat

| Komponen | Perintah cek |
|----------|----------------|
| Backend hidup? | Buka http://localhost:8000/health |
| Frontend hidup? | Buka http://localhost:3000 |
| API docs | http://localhost:8000/docs |

---

*Dokumen ini merupakan panduan operasional untuk membuka dan menggunakan source code Sentimen KPwBI Bali.*
