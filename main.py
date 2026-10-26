import tkinter as tk
from winupdate import request_admin_privileges
from ui import WinUpdateApp

if __name__ == "__main__":
    request_admin_privileges()

    root = tk.Tk()
    app = WinUpdateApp(root)
    root.mainloop()

