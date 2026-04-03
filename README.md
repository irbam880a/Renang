# 🏊 Renang – Swimming Timer ESP32

Timer renang 16 lintasan berbasis **ESP32** dengan backend **Node.js + SQLite** dan dashboard web real-time.

---

## Fitur

| Fitur | Detail |
|---|---|
| **16 Lintasan** | Sensor selesai per lintasan (active-LOW) |
| **2 Tombol Start** | Start A (Heat 1) dan Start B (Heat 2) |
| **1 Tombol Reset** | Reset semua lintasan + database |
| **Database** | SQLite via `node:sqlite` (built-in Node.js ≥ 22.5) |
| **Dashboard Web** | Real-time ranking, podium emas/perak/perunggu, riwayat lomba |
| **REST API** | ESP32 kirim waktu via HTTP POST |

---

## Arsitektur Sistem

```
[ESP32]                        [Server (PC/Raspberry Pi)]
  ├─ 16 sensor lintasan  →  POST /api/finish  → [SQLite DB]
  ├─ Tombol Start A/B    →  POST /api/start        ↑
  └─ Tombol Reset        →  POST /api/reset    GET /api/results
                                                    ↑
                                            [Browser Dashboard]
```

---

## Struktur Proyek

```
Renang/
├── firmware/
│   └── swimming_timer/
│       └── swimming_timer.ino   # Kode ESP32 (Arduino)
└── backend/
    ├── server.js                # Express REST API
    ├── database.js              # Layer database SQLite
    ├── package.json
    ├── public/
    │   └── index.html           # Dashboard web
    └── tests/
        └── api.test.js          # Tes otomatis (node:test)
```

---

## Skema Kabel ESP32

| Komponen | GPIO | Catatan |
|---|---|---|
| Lintasan 1 | GPIO 4 | INPUT_PULLUP |
| Lintasan 2 | GPIO 5 | INPUT_PULLUP |
| Lintasan 3 | GPIO 13 | INPUT_PULLUP |
| Lintasan 4 | GPIO 14 | INPUT_PULLUP |
| Lintasan 5 | GPIO 15 | INPUT_PULLUP |
| Lintasan 6 | GPIO 16 | INPUT_PULLUP |
| Lintasan 7 | GPIO 17 | INPUT_PULLUP |
| Lintasan 8 | GPIO 18 | INPUT_PULLUP |
| Lintasan 9 | GPIO 25 | INPUT_PULLUP |
| Lintasan 10 | GPIO 26 | INPUT_PULLUP |
| Lintasan 11 | GPIO 27 | INPUT_PULLUP |
| Lintasan 12 | GPIO 32 | INPUT_PULLUP |
| Lintasan 13 | GPIO 33 | **External pull-up 10 kΩ ke 3V3** |
| Lintasan 14 | GPIO 34 | **External pull-up 10 kΩ ke 3V3** |
| Lintasan 15 | GPIO 35 | **External pull-up 10 kΩ ke 3V3** |
| Lintasan 16 | GPIO 36 | **External pull-up 10 kΩ ke 3V3** |
| **Tombol Start A** | GPIO 19 | INPUT_PULLUP |
| **Tombol Start B** | GPIO 21 | INPUT_PULLUP |
| **Tombol Reset** | GPIO 22 | INPUT_PULLUP |

> Semua sensor/tombol: satu kaki ke pin GPIO, kaki lainnya ke **GND**.

---

## Setup Backend

### Prasyarat
- **Node.js ≥ 22.5** (menggunakan `node:sqlite` built-in)

```bash
cd backend
npm install
```

### Jalankan server

```bash
node --experimental-sqlite server.js
# Server berjalan di http://0.0.0.0:3000
```

Buka browser ke **http://\<IP-SERVER\>:3000** untuk melihat dashboard.

### Jalankan tes

```bash
cd backend
npm test
```

---

## Setup Firmware ESP32

### Library Arduino yang diperlukan
- **ArduinoJson** (v6 atau v7) – install via Arduino Library Manager

### Konfigurasi
Edit bagian berikut di `firmware/swimming_timer/swimming_timer.ino`:

```cpp
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";
const char* SERVER_BASE   = "http://192.168.1.100:3000";  // IP server
```

Upload ke ESP32 menggunakan Arduino IDE.

---

## REST API

| Method | Path | Body | Deskripsi |
|---|---|---|---|
| `POST` | `/api/start` | `{ "heat": 1 }` | Mulai perlombaan heat 1 atau 2 |
| `POST` | `/api/finish` | `{ "lane": 3, "heat": 1, "elapsedMs": 62500 }` | Catat waktu selesai lintasan |
| `POST` | `/api/reset` | `{}` | Reset semua lintasan |
| `GET` | `/api/results` | — | Hasil perlombaan aktif |
| `GET` | `/api/races` | — | Riwayat semua perlombaan |

---

## Cara Pakai

1. Nyalakan server backend di PC/Raspberry Pi.
2. Pastikan ESP32 dan server dalam **jaringan WiFi yang sama**.
3. Upload firmware ke ESP32.
4. Tekan **Start A** → Heat 1 dimulai (semua timer reset).
5. Tekan **Start B** → Heat 2 dimulai.
6. Tiap perenang menyentuh sensor → waktu lintasan otomatis tercatat.
7. Dashboard web tampilkan ranking real-time dengan podium 🥇🥈🥉.
8. Tekan **Reset** → semua data lintasan dihapus, siap lomba baru.
