"""Entry point for the Swimming Competition Timer application."""

import sys


def _check_dependencies():
    """Check that required packages are installed and print helpful messages."""
    missing = []
    try:
        import tkinter  # noqa: F401
    except ImportError:
        missing.append("tkinter  (install: apt install python3-tk  or reinstall Python with Tk support)")
    try:
        import serial  # noqa: F401
    except ImportError:
        missing.append("pyserial (install: pip install pyserial)")
    if missing:
        print("ERROR: Missing required dependencies:\n")
        for m in missing:
            print(f"  - {m}")
        print("\nInstall all requirements with:  pip install -r requirements.txt")
        print("For tkinter on Windows, reinstall Python and tick 'tcl/tk' option.")
        sys.exit(1)


def main():
    _check_dependencies()
    import tkinter as tk
    from gui.main_window import MainWindow

    root = tk.Tk()
    root.resizable(True, True)
    app = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
