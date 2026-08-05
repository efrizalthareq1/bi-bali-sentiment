# Tutorial: Memasukkan Session ID & CSRF Token Instagram (Opsi B)

Panduan ini menjelaskan cara mengambil cookie Instagram dari browser dan memasukkannya ke **Railway**, agar dashboard bisa menarik **komentar asli** dari akun [@qrissummerrun](https://www.instagram.com/qrissummerrun/) dan menganalisis sentimennya.

> **Penting:** Anda **tidak** perlu memberikan password Instagram ke siapa pun. Yang dipakai hanya dua nilai cookie dari browser Anda sendiri.

---

## Apa yang akan diisi?

| Nama di Railway | Cookie Instagram | Fungsi |
|-----------------|------------------|--------|
| `INSTAGRAM_SESSION_ID` | `sessionid` | Bukti Anda sudah login |
| `INSTAGRAM_CSRF_TOKEN` | `csrftoken` | Token keamanan permintaan API |

Opsional (jika sync masih gagal):

| Nama di Railway | Cookie Instagram |
|-----------------|------------------|
| `INSTAGRAM_DS_USER_ID` | `ds_user_id` |

---

## Prasyarat

1. Akun Instagram yang **sudah login** di browser (Chrome atau Edge disarankan).
2. Akun tersebut bisa **melihat** profil dan komentar [@qrissummerrun](https://www.instagram.com/qrissummerrun/).
3. Akses ke [Railway](https://railway.app) project **bi-bali-sentiment**, service **api**.

---

## Langkah 1 — Login Instagram di browser

1. Buka https://www.instagram.com  
2. Login dengan akun Anda (bukan password yang dikirim ke sistem — cukup login normal di browser).
3. Buka https://www.instagram.com/qrissummerrun/ dan pastikan halaman profil tampil normal.

---

## Langkah 2 — Buka Developer Tools (cookie)

### Google Chrome / Microsoft Edge

1. Di halaman Instagram, tekan **F12** (atau klik kanan → **Inspect** / **Periksa**).
2. Pilih tab **Application** (Chrome) atau **Aplikasi** (Edge).
   - Jika tidak terlihat: klik ikon **>>** di bar tab DevTools.
3. Di panel kiri, buka:
   ```
   Storage → Cookies → https://www.instagram.com
   ```
4. Di tabel kanan, cari baris:
   - **`sessionid`** — klik sekali, salin **Value** (panjang, biasanya puluhan karakter).
   - **`csrftoken`** — salin **Value**-nya juga.

### Mozilla Firefox

1. Tekan **F12** → tab **Storage** → **Cookies** → `https://www.instagram.com`
2. Salin nilai `sessionid` dan `csrftoken`.

---

## Langkah 3 — Salin dengan benar

Saat menyalin ke Railway:

- Salin **hanya nilai** (Value), **bukan** nama cookie.
- **Jangan** tambahkan tanda kutip `"` di awal/akhir.
- **Jangan** ada spasi di depan atau belakang.
- Cookie `sessionid` biasanya berakhir dengan `==` atau karakter acak panjang — itu normal.

Contoh format yang **salah**:
```
"1234567890abcdef%3A..."
 sessionid=123456...
```

Contoh format yang **benar** (isi asli Anda akan berbeda):
```
1234567890abcdef%3A1%3A...
```

---

## Langkah 4 — Masukkan ke Railway

1. Buka https://railway.app dan login.
2. Masuk ke project **bi-bali-sentiment**.
3. Klik service **api** (backend FastAPI).
4. Buka tab **Variables**.
5. Klik **+ New Variable** dan tambahkan satu per satu:

| Variable name | Value |
|---------------|--------|
| `INSTAGRAM_SESSION_ID` | paste nilai `sessionid` |
| `INSTAGRAM_CSRF_TOKEN` | paste nilai `csrftoken` |

6. Klik **Save** / **Deploy** jika Railway meminta redeploy.
7. Tunggu deploy selesai (status service **Online**, biasanya 1–3 menit).

---

## Langkah 5 — Uji di dashboard

1. Buka https://bi-bali-sentiment.vercel.app/dashboard  
2. Scroll ke panel **Sentimen Komentar @qrissummerrun**  
3. Klik **Tarik komentar asli**  
4. Tunggu beberapa detik — komentar netizen akan muncul dengan label **Positif / Negatif / Netral**

### Cek cookie dulu (di browser)

Buka URL ini **setelah redeploy api**:

```
https://api-production-58a9.up.railway.app/ingest/instagram-comments/diagnostic?username=qrissummerrun
```

Contoh respons jika cookie **belum terbaca**:
```json
{
  "session_configured": false,
  "session_id_length": 0,
  "hint": "INSTAGRAM_SESSION_ID belum terdeteksi di server api..."
}
```

Contoh respons jika cookie **valid**:
```json
{
  "session_configured": true,
  "session_id_length": 77,
  "profile_status": 200,
  "media_posts_found": 12,
  "comments_found_sample": 8,
  "ok": true,
  "hint": "Cookie valid. Jalankan POST /ingest/instagram-comments untuk sinkronisasi."
}
```

### Opsional: tambahkan `ds_user_id`

Jika diagnostic menunjukkan profil OK tapi komentar ditolak (401/403), salin juga cookie **`ds_user_id`** dari browser dan tambahkan di Railway:

| Variable | Cookie |
|----------|--------|
| `INSTAGRAM_DS_USER_ID` | `ds_user_id` |

---

## Langkah 6 — Uji lewat API (opsional)

Buka di browser atau Postman:

```
POST https://api-production-58a9.up.railway.app/ingest/instagram-comments?username=qrissummerrun
```

Respons sukses contoh:
```json
{
  "inserted": 25,
  "skipped": 3,
  "message": "@qrissummerrun: 25 baru (20 komentar dalam batch), 3 dilewati, 25 dianalisis."
}
```

Cek ringkasan:
```
GET https://api-production-58a9.up.railway.app/dashboard/instagram-comments?username=qrissummerrun
```

---

## Pengaturan lokal (jika menjalankan backend di komputer sendiri)

Salin ke file `backend/.env`:

```env
INSTAGRAM_SESSION_ID=isi_sessionid_anda
INSTAGRAM_CSRF_TOKEN=isi_csrftoken_anda
INSTAGRAM_MONITOR_USERNAME=qrissummerrun
```

Lalu restart backend:
```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

---

## Troubleshooting

| Gejala | Penyebab umum | Solusi |
|--------|---------------|--------|
| `inserted: 0`, pesan "belum terdeteksi" | Variable di service yang salah / belum redeploy | Pastikan variable di service **api** (bukan postgres), klik **Deploy**, tunggu selesai |
| `session_configured: false` di diagnostic | Sama seperti di atas | Redeploy service api setelah save variable |
| `inserted: 0` setelah variable diisi | Cookie kedaluwarsa atau logout | Login ulang IG → salin **sessionid** & **csrftoken** baru → update Railway |
| Nilai cookie ada tanda `"` | Salin dengan kutip | Hapus kutip di Railway, simpan ulang |
| Sync berhasil tapi 0 komentar | Akun IG tidak bisa akses komentar @qrissummerrun | Gunakan akun yang bisa lihat komentar di postingan event |
| Error 401 / 403 di log | Session invalid | Ulangi Langkah 1–4 dengan cookie fresh |
| Cookie hilang setelah beberapa hari | Instagram mengexpire session | Normal — ulangi proses salin cookie (biasanya tiap 1–4 minggu) |

---

## Keamanan

- **Jangan** kirim `sessionid` lewat chat, email, atau screenshot ke orang lain.
- **Jangan** commit file `.env` ke Git.
- Jika cookie bocor, logout Instagram di semua perangkat → login lagi → cookie lama otomatis tidak valid.
- Untuk production jangka panjang, pertimbangkan **Meta Graph API** (Opsi A) dengan akun Business resmi @qrissummerrun.

---

## Ringkasan cepat

```
Login IG di Chrome
    → F12 → Application → Cookies → instagram.com
    → Salin sessionid + csrftoken
    → Railway → api → Variables
    → INSTAGRAM_SESSION_ID + INSTAGRAM_CSRF_TOKEN
    → Deploy → Dashboard → Tarik komentar asli
```

---

*Dokumen ini untuk fitur Sentimen Komentar Instagram pada dashboard Sentimen KPwBI Bali.*
