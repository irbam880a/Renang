"""Entry point for the Swimming Competition Timer application."""

import sys
import traceback


def _check_python_version():
    """Ensure Python 3.7+ is being used."""
    if sys.version_info < (3, 7):
        print(
            f"ERROR: Python 3.7 atau lebih baru diperlukan.\n"
            f"       Versi Anda: {sys.version}\n"
            f"       Silakan instal Python terbaru dari https://www.python.org"
        )
        sys.exit(1)


def _check_dependencies():
    """Check that required packages are installed and print helpful messages."""
    missing = []
    try:
        import tkinter  # noqa: F401
    except ImportError:
        missing.append("tkinter  (install: apt install python3-tk  atau reinstall Python dengan opsi tcl/tk)")
    try:
        import serial  # noqa: F401
    except ImportError:
        missing.append("pyserial (install: pip install pyserial)")
    if missing:
        print("ERROR: Dependensi yang diperlukan belum terinstal:\n")
        for m in missing:
            print(f"  - {m}")
        print("\nInstal semua dependensi dengan:  pip install -r requirements.txt")
        print("Untuk tkinter di Windows, reinstall Python dan centang opsi 'tcl/tk and IDLE'.")
        sys.exit(1)


def main():
    _check_python_version()
    _check_dependencies()

    try:
        import tkinter as tk
        from gui.main_window import MainWindow

        root = tk.Tk()
        root.resizable(True, True)
        MainWindow(root)
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
    except Exception as exc:
        print("\n" + "=" * 60)
        print("ERROR: Aplikasi gagal dijalankan.")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        print(f"\nPython version: {sys.version}")
        print(f"Platform: {sys.platform}")
        print("\nSaran perbaikan:")
        print("  1. Pastikan semua dependensi terinstal:")
        print("     pip install -r requirements.txt")
        print("  2. Pastikan menggunakan Python 3.7 atau lebih baru")
        print("  3. Salin SELURUH pesan error di atas jika ingin melaporkan bug")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
