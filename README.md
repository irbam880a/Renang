# 🏊 Sistem Timer Renang

Aplikasi Python GUI + ESP32 untuk pencatatan waktu lomba renang.

---

## Fitur

| Fitur | Keterangan |
|---|---|
| **Timer per lintasan** | Hingga 16 lintasan, kartu timer individual dengan tombol STOP |
| **Start / Reset** | Tombol **START LOMBA** dan **RESET SEMUA** |
| **Integrasi ESP32** | Terima sinyal sensor sentuh dari ESP32 melalui USB-Serial |
| **Database** | SQLite – kompetisi, acara, heat, dan hasil tersimpan permanen |
| **Ekspor Excel** | Satu sheet per acara + sheet rekapitulasi (`openpyxl`) |
| **Ekspor PDF** | Format *landscape* A4 dengan header buku acara (`reportlab`) |
| **Fleksibel** | Jumlah lintasan dapat diatur 1–16, tanpa batas jumlah acara/heat |

---

## Struktur Data (Buku Acara)

```
Kompetisi  (KEJURKAB TAHUN 2024)
 └── Acara  (No. Acara, Seri, Jarak, Gaya, Kategori)
      └── Heat  (Heat 1, Heat 2, ...)
           └── Hasil  (Lintasan, Nama Atlet, Sekolah, Waktu, Keterangan)
```

---

## Instalasi

```bash
pip install -r requirements.txt
```

> Membutuhkan Python 3.7+ dengan `tkinter` (termasuk di instalasi standar Python dari python.org).

---

## Menjalankan

```bash
python main.py
```

---

## Tab Aplikasi

### ⏱ Timer
1. Pilih **Kompetisi → Acara → Heat** dari dropdown.
2. Klik **Input Atlet** untuk mengisi nama atlet dan sekolah per lintasan.
3. Klik **▶ START LOMBA** untuk memulai stopwatch semua lintasan sekaligus.
4. Klik **STOP** pada kartu lintasan (atau tekan sensor di ESP32) saat perenang menyentuh finish.
5. Klik **⏹ RESET SEMUA** untuk mengulang.
6. Klik **Simpan Hasil** untuk menyimpan waktu ke database.

### 📋 Setup Kompetisi
Kelola hierarki **Kompetisi → Acara → Heat** dan isi data atlet per lintasan.

### 🏆 Hasil Lomba
Tampilkan dan filter hasil yang sudah tersimpan, terurut otomatis berdasarkan waktu.

### 💾 Ekspor
Ekspor hasil ke **Excel (.xlsx)** atau **PDF (.pdf)** dalam format Buku Acara.

---

## Pengaturan ESP32

1. Upload `esp32_firmware/swimming_timer.ino` ke board ESP32.
2. Di aplikasi, buka **⚙ Pengaturan** → pilih port COM dan baud rate (default 115200).
3. Klik **Hubungkan ESP32**.

### Protokol Serial

| Arah | Perintah | Keterangan |
|---|---|---|
| PC → ESP32 | `START\n` | Mulai semua timer |
| PC → ESP32 | `RESET\n` | Reset semua timer |
| PC → ESP32 | `STOP:<N>\n` | Stop lintasan N dari PC |
| PC → ESP32 | `PING\n` | Cek koneksi |
| ESP32 → PC | `STARTED\n` | Timer berjalan |
| ESP32 → PC | `RESET_OK\n` | Reset dikonfirmasi |
| ESP32 → PC | `LANE:<N>:TIME:<ms>\n` | Lintasan N selesai di `<ms>` milidetik |
| ESP32 → PC | `PONG\n` | Respons PING |

### Pin ESP32 (dapat disesuaikan di `.ino`)

| Komponen | Pin Default |
|---|---|
| Tombol Start | GPIO 0 (BOOT) |
| LED Status | GPIO 2 (built-in) |
| Sensor Lintasan 1–8 | GPIO 4, 5, 13, 14, 15, 16, 17, 18 |
| Sensor Lintasan 9–16 | GPIO 19, 21, 22, 23, 25, 26, 27, 32 |

---

## Dependensi

```
openpyxl>=3.1.0
reportlab>=4.0.0
pyserial>=3.5
Pillow>=10.0.0
```
