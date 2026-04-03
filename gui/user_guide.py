"""User guide tab – scrollable help page with usage instructions."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from gui import theme

# ── Guide Content ────────────────────────────────────────────────────────────
# Each section is a (title, body) tuple. Body may contain multiple paragraphs
# separated by double newlines.

GUIDE_SECTIONS = [
    (
        "Selamat Datang",
        "Sistem Timer Renang adalah aplikasi pencatat waktu lomba renang yang "
        "mendukung multi-lintasan, koneksi perangkat ESP32, serta ekspor dan cetak "
        "hasil lomba. Aplikasi ini dirancang untuk membantu panitia lomba renang "
        "mengelola kompetisi dari awal hingga akhir."
    ),
    (
        "1. Setup Kompetisi",
        "Langkah pertama adalah membuat data kompetisi:\n\n"
        "a) Buka tab \"📋 Setup Kompetisi\".\n"
        "b) Klik tombol \"＋ Baru\" di panel Kompetisi untuk membuat kompetisi baru.\n"
        "c) Isi nama kompetisi, tahun, tanggal, venue, dan jumlah lintasan.\n"
        "d) Klik \"Simpan\".\n\n"
        "Setelah kompetisi dibuat, Anda bisa mengeditnya dengan tombol \"✏ Edit\" "
        "atau menghapusnya dengan tombol \"🗑 Hapus\"."
    ),
    (
        "2. Tambah Acara (Event)",
        "Setelah kompetisi dibuat:\n\n"
        "a) Pilih kompetisi di daftar sebelah kiri.\n"
        "b) Klik \"＋ Baru\" di panel Acara.\n"
        "c) Isi nomor acara, seri/tahun lahir, jarak (meter), gaya renang, "
        "dan kategori (putra/putri).\n"
        "d) Klik \"Simpan\".\n\n"
        "Anda bisa menambahkan banyak acara dalam satu kompetisi."
    ),
    (
        "3. Tambah Heat",
        "Setiap acara bisa memiliki beberapa heat:\n\n"
        "a) Pilih acara di daftar tengah.\n"
        "b) Klik \"＋ Heat\" di panel Heat.\n"
        "c) Heat baru akan ditambahkan secara otomatis dengan nomor urut.\n\n"
        "Untuk memasukkan data atlet per lintasan, pilih heat lalu klik "
        "\"👤 Input Atlet\"."
    ),
    (
        "4. Input Data Atlet",
        "Dialog input atlet menampilkan semua lintasan yang tersedia:\n\n"
        "a) Isi nama atlet dan asal sekolah/klub untuk setiap lintasan.\n"
        "b) Kolom keterangan bisa diisi dengan informasi tambahan.\n"
        "c) Klik \"Simpan\" untuk menyimpan data.\n\n"
        "Data atlet bisa diinput dari tab Setup Kompetisi maupun dari tab Timer."
    ),
    (
        "5. Menggunakan Timer",
        "Tab Timer adalah inti dari aplikasi ini:\n\n"
        "a) Buka tab \"⏱ Timer\".\n"
        "b) Pilih Kompetisi → Acara → Heat dari dropdown di bagian atas.\n"
        "c) Data atlet akan otomatis dimuat ke kartu lintasan.\n"
        "d) Klik tombol hijau \"▶ START LOMBA\" untuk memulai pencatatan waktu.\n"
        "e) Semua kartu lintasan akan mulai menghitung waktu.\n"
        "f) Klik tombol \"■ STOP\" pada setiap lintasan saat perenang finish.\n"
        "g) Waktu akan tercatat dan status berubah menjadi \"✓ SELESAI\".\n"
        "h) Klik \"💾 Simpan Hasil\" untuk menyimpan semua waktu ke database.\n\n"
        "Tombol \"⏹ RESET SEMUA\" akan mereset semua timer ke awal."
    ),
    (
        "6. Koneksi ESP32 (Opsional)",
        "Jika Anda menggunakan perangkat ESP32 untuk pencatatan waktu otomatis:\n\n"
        "a) Buka Pengaturan melalui tab \"💾 Ekspor\" → \"⚙ Pengaturan\".\n"
        "b) Pilih port serial ESP32 dan baud rate.\n"
        "c) Klik \"⚡ Hubungkan ESP32\" di header aplikasi.\n"
        "d) Indikator status akan berubah hijau jika berhasil terhubung.\n\n"
        "Saat ESP32 terhubung, timer setiap lintasan akan otomatis berhenti "
        "ketika sensor touchpad tersentuh oleh perenang."
    ),
    (
        "7. Melihat Hasil Lomba",
        "Untuk melihat hasil yang sudah tersimpan:\n\n"
        "a) Buka tab \"🏆 Hasil Lomba\".\n"
        "b) Pilih kompetisi dari dropdown.\n"
        "c) Klik \"📊 Tampilkan\".\n"
        "d) Gunakan filter Acara untuk melihat hasil per acara.\n"
        "e) Peringkat 1-3 akan ditandai dengan warna khusus.\n\n"
        "Hasil lomba diurutkan berdasarkan nomor acara, heat, dan lintasan."
    ),
    (
        "8. Cetak Hasil",
        "Untuk mencetak hasil lomba ke kertas:\n\n"
        "a) Buka tab \"🏆 Hasil Lomba\".\n"
        "b) Pilih kompetisi dan klik \"📊 Tampilkan\".\n"
        "c) Klik tombol \"🖨 Cetak Hasil\" di kanan atas.\n"
        "d) Sebuah file PDF akan dibuat dan dibuka otomatis.\n"
        "e) Gunakan menu print (Ctrl+P) di aplikasi PDF viewer untuk mencetak.\n\n"
        "Pada Windows, dialog cetak akan langsung terbuka secara otomatis."
    ),
    (
        "9. Ekspor Data",
        "Hasil lomba dapat diekspor dalam dua format:\n\n"
        "a) Buka tab \"💾 Ekspor\".\n"
        "b) Pilih kompetisi yang ingin diekspor.\n"
        "c) Klik \"📊 Ekspor ke Excel\" untuk format .xlsx.\n"
        "d) Klik \"📄 Ekspor ke PDF\" untuk format .pdf.\n"
        "e) Pilih lokasi penyimpanan file.\n\n"
        "File Excel berisi sheet per acara dan sheet rekapitulasi.\n"
        "File PDF berisi buku acara lengkap dengan tabel hasil."
    ),
    (
        "10. Tips & Catatan",
        "• Pastikan data atlet sudah lengkap sebelum memulai timer.\n"
        "• Simpan hasil segera setelah semua lintasan selesai.\n"
        "• Peringkat dihitung otomatis berdasarkan waktu tercepat per heat.\n"
        "• Data tersimpan di file database lokal (renang.db).\n"
        "• Backup file renang.db secara berkala untuk menghindari kehilangan data.\n"
        "• Jika timer tidak berjalan, pastikan heat sudah dipilih dengan benar.\n"
        "• Untuk mereset data, hapus kompetisi di tab Setup Kompetisi."
    ),
]


# ── Widget ───────────────────────────────────────────────────────────────────

class UserGuideTab(ttk.Frame):
    """Scrollable help / user-guide tab."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # Outer container for the scrollable area
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=8)

        canvas = tk.Canvas(container, bg=theme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._inner = tk.Frame(canvas, bg=theme.BG_CARD)

        self._inner.bind("<Configure>",
                         lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Enable mouse-wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-3, "units")

        def _on_linux_scroll_down(event):
            canvas.yview_scroll(3, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_linux_scroll_up)
        canvas.bind_all("<Button-5>", _on_linux_scroll_down)

        # ── Header ───────────────────────────────────────────────────────
        hdr = tk.Frame(self._inner, bg=theme.PRIMARY, height=56)
        hdr.pack(fill="x", padx=0, pady=(0, 12))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📖  PANDUAN PENGGUNAAN APLIKASI",
                 font=theme.FONT_HEADER, fg=theme.TEXT_ON_PRIMARY,
                 bg=theme.PRIMARY).pack(side="left", padx=16, pady=10)

        # ── Sections ─────────────────────────────────────────────────────
        for title, body in GUIDE_SECTIONS:
            self._add_section(title, body)

        # Bottom spacer
        tk.Frame(self._inner, bg=theme.BG_CARD, height=20).pack()

    def _add_section(self, title: str, body: str):
        """Add a collapsible-looking section card."""
        card = tk.Frame(self._inner, bg=theme.BG_CARD, padx=16, pady=8,
                        highlightbackground=theme.BORDER_LIGHT, highlightthickness=1)
        card.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(card, text=title,
                 font=theme.FONT_SUBTITLE, fg=theme.PRIMARY,
                 bg=theme.BG_CARD, anchor="w").pack(fill="x", pady=(4, 2))

        tk.Label(card, text=body,
                 font=theme.FONT_BODY, fg=theme.TEXT_SECONDARY,
                 bg=theme.BG_CARD, anchor="nw", justify="left",
                 wraplength=750).pack(fill="x", pady=(0, 4))
