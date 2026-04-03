# Swimming Timer – Python GUI

Aplikasi GUI desktop untuk timer renang 16 lintasan.  
Berjalan **standalone** (tanpa Node.js server) menggunakan SQLite bawaan.

## Prasyarat

| Dependensi | Catatan |
|---|---|
| **Python 3.8+** | Sudah termasuk tkinter, sqlite3, webbrowser |
| **tkinter** | Bawaan Python di Windows & macOS. Di Ubuntu/Debian: `sudo apt install python3-tk` |

Tidak ada paket `pip` yang perlu diinstall.

## Jalankan

```bash
# Default – database baru di gui/swimming_timer.db
python3 swimming_timer_gui.py

# Gunakan database yang sama dengan Node.js backend
DB_PATH=../backend/swimming_timer.db python3 swimming_timer_gui.py
```

## Fitur

### ⏱ Tab Timer
| Elemen | Fungsi |
|---|---|
| Status bar | Status lomba, Heat A/B, stopwatch berjalan |
| 16 kartu lintasan | Nama atlet, waktu tercatat, lencana 🥇🥈🥉 |
| Tombol **SELESAI** | Catat waktu lintasan secara manual |
| **▶ START A** | Mulai perlombaan Heat A |
| **▶ START B** | Mulai perlombaan Heat B |
| **↺ RESET** | Reset semua lintasan (data dihapus dari DB) |

### ⚙ Tab Setup Lomba
- Isi **Nama Lomba, Tanggal, Kategori, Acara, Seri, Nomor, Gaya, Gender**  
- Isi **Nama Atlet, Klub/Sekolah, Limid Waktu** untuk semua 16 lintasan  
- Klik **💾 Simpan Setup** → tersimpan ke database  
- Klik **🔄 Muat Data Aktif** → memuat data lomba yang sedang berjalan

### 🖨 Tab Laporan
| Laporan | Format | Keterangan |
|---|---|---|
| **Form Catatan Waktu** | A5 portrait × 16 lembar | Satu form per lintasan untuk juri pencatat waktu |
| **Buku Acara** | A4 landscape | Semua acara dalam tabel – nama atlet, limid waktu, waktu tercatat |

Laporan dibuka di browser default, kemudian pilih **Cetak** (Ctrl+P).

### 📋 Tab Riwayat
- Tabel semua lomba historis  
- Pilih baris lalu klik **🖨 Cetak Terpilih** → cetak Form Catatan Waktu lomba tersebut

## Berbagi Database dengan Node.js Backend

Set `DB_PATH` ke path database backend agar kedua sistem memakai data yang sama:

```bash
# Linux/macOS
export DB_PATH="$(pwd)/../backend/swimming_timer.db"
python3 swimming_timer_gui.py

# Windows
set DB_PATH=..\backend\swimming_timer.db
python swimming_timer_gui.py
```

ESP32 → mengirim waktu ke Node.js backend (port 3000) → tersimpan di database yang sama → GUI Python baca data yang sama.

## Wiring ESP32 (untuk integrasi hardware)

Lihat `../README.md` untuk diagram pin lengkap.  
Tombol START A/B dan RESET pada ESP32 akan mengirim POST ke Node.js backend;  
Python GUI bisa membaca hasilnya langsung dari database yang di-share.
