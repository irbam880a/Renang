"""Entry point for the Swimming Competition Timer application."""

import tkinter as tk
from gui.main_window import MainWindow


def main():
    root = tk.Tk()
    root.resizable(True, True)
    app = MainWindow(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
