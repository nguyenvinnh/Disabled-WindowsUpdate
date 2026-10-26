import tkinter as tk
from tkinter import messagebox
from winupdate import (
    get_windows_update_status, disable_windows_update, enable_windows_update, restart_computer,
    STATE_ENABLED, STATE_DISABLED, STATE_PARTIAL
)

# ===== Bảng màu =====
BG = "#f3f4f6"          # nền cửa sổ
CARD_BG = "#ffffff"     # nền thẻ trạng thái
TEXT_DARK = "#111827"
TEXT_MUTED = "#6b7280"
BORDER = "#e5e7eb"
HEADER_BG = "#1e3a8a"

GREEN = "#16a34a"
GREEN_HOVER = "#15803d"
RED = "#dc2626"
RED_HOVER = "#b91c1c"
AMBER = "#d97706"

FONT = "Segoe UI"
AUTO_REFRESH_MS = 5000   # tự quét lại trạng thái mỗi 5 giây


class WinUpdateApp:
    def __init__(self, root):
        self.root = root
        self.root.title("tắt Windows Update")
        self.root.geometry("460x400")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.state = STATE_ENABLED
        self.busy = False
        self.btn_colors = (RED, RED_HOVER)

        self.build_header()
        self.build_status_card()
        self.build_action_area()
        self.build_footer()

        self.center_window()
        self.update_ui_status()
        self.root.after(AUTO_REFRESH_MS, self.auto_refresh)

    # ------------------------------------------------------------------
    # Dựng giao diện
    # ------------------------------------------------------------------
    def build_header(self):
        header = tk.Frame(self.root, bg=HEADER_BG, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="QUẢN LÝ WINDOWS UPDATE",
            font=(FONT, 14, "bold"), bg=HEADER_BG, fg="white"
        ).pack(expand=True)

    def build_status_card(self):
        # Viền mỏng quanh thẻ
        border = tk.Frame(self.root, bg=BORDER)
        border.pack(fill="x", padx=30, pady=(25, 10))

        card = tk.Frame(border, bg=CARD_BG)
        card.pack(fill="x", padx=1, pady=1)

        tk.Label(
            card, text="TRẠNG THÁI HIỆN TẠI",
            font=(FONT, 9, "bold"), bg=CARD_BG, fg=TEXT_MUTED
        ).pack(pady=(15, 8))

        # Hàng chứa chấm tròn + chữ trạng thái
        row = tk.Frame(card, bg=CARD_BG)
        row.pack()

        self.dot = tk.Canvas(row, width=18, height=18, bg=CARD_BG, highlightthickness=0)
        self.dot_item = self.dot.create_oval(2, 2, 16, 16, fill="gray", outline="")
        self.dot.pack(side="left", padx=(0, 8))

        self.status_label = tk.Label(
            row, text="Đang kiểm tra...",
            font=(FONT, 15, "bold"), bg=CARD_BG, fg="gray"
        )
        self.status_label.pack(side="left")

        self.status_desc = tk.Label(
            card, text="", font=(FONT, 9),
            bg=CARD_BG, fg=TEXT_MUTED
        )
        self.status_desc.pack(pady=(6, 4))

        self.status_detail = tk.Label(
            card, text="", font=(FONT, 9, "bold"),
            bg=CARD_BG, fg=TEXT_DARK
        )
        self.status_detail.pack(pady=(0, 15))

    def build_action_area(self):
        self.action_btn = tk.Label(
            self.root, text="...", font=(FONT, 12, "bold"),
            fg="white", bg=RED, cursor="hand2", pady=12
        )
        self.action_btn.pack(fill="x", padx=30, pady=(10, 8))

        self.action_btn.bind("<Button-1>", lambda e: self.toggle_update())
        self.action_btn.bind("<Enter>", self.on_btn_enter)
        self.action_btn.bind("<Leave>", self.on_btn_leave)

        self.refresh_btn = tk.Label(
            self.root, text="⟳  Quét lại trạng thái",
            font=(FONT, 10), bg=BG, fg=HEADER_BG, cursor="hand2"
        )
        self.refresh_btn.pack(pady=(6, 0))
        self.refresh_btn.bind("<Button-1>", lambda e: self.update_ui_status())
        self.refresh_btn.bind("<Enter>", lambda e: self.refresh_btn.config(fg="#3b82f6"))
        self.refresh_btn.bind("<Leave>", lambda e: self.refresh_btn.config(fg=HEADER_BG))

    def build_footer(self):
        footer = tk.Frame(self.root, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(0, 10))

        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x", padx=30, pady=(0, 8))
        tk.Label(
            footer, text="Đang chạy với quyền Administrator",
            font=(FONT, 8), bg=BG, fg=TEXT_MUTED
        ).pack()

    # ------------------------------------------------------------------
    # Hiệu ứng nút
    # ------------------------------------------------------------------
    def on_btn_enter(self, _event):
        if not self.busy:
            self.action_btn.config(bg=self.btn_colors[1])

    def on_btn_leave(self, _event):
        if not self.busy:
            self.action_btn.config(bg=self.btn_colors[0])

    def set_busy(self, busy):
        """Khóa nút khi đang xử lý để tránh bấm nhiều lần"""
        self.busy = busy
        if busy:
            self.action_btn.config(text="Đang xử lý...", bg="#9ca3af", cursor="watch")
            self.refresh_btn.config(fg="#9ca3af", cursor="watch")
        else:
            self.action_btn.config(cursor="hand2")
            self.refresh_btn.config(fg=HEADER_BG, cursor="hand2")
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Căn giữa cửa sổ
    # ------------------------------------------------------------------
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Cập nhật trạng thái
    # ------------------------------------------------------------------
    def auto_refresh(self):
        """Tự quét lại định kỳ để bắt kịp khi Windows tự thay đổi cấu hình"""
        self.update_ui_status()
        self.root.after(AUTO_REFRESH_MS, self.auto_refresh)

    def update_ui_status(self):
        """Cập nhật giao diện theo trạng thái thực tế"""
        if self.busy:
            return

        self.state, details = get_windows_update_status()

        service_txt = "đã khóa" if details["service_locked"] else "đang mở"
        policy_txt = "đã khóa" if details["policy_locked"] else "chưa khóa"
        self.status_detail.config(text=f"Dịch vụ: {service_txt}   •   Registry: {policy_txt}")

        if self.state == STATE_ENABLED:
            self.dot.itemconfig(self.dot_item, fill=GREEN)
            self.status_label.config(text="ĐANG BẬT", fg=GREEN)
            self.status_desc.config(text="Windows có thể tự động tải và cài đặt bản cập nhật")
            self.btn_colors = (RED, RED_HOVER)
            self.action_btn.config(text="TẮT WINDOWS UPDATE", bg=RED)

        elif self.state == STATE_DISABLED:
            self.dot.itemconfig(self.dot_item, fill=RED)
            self.status_label.config(text="ĐÃ TẮT", fg=RED)
            self.status_desc.config(text="Windows Update đã bị khóa bằng Dịch vụ và Registry")
            self.btn_colors = (GREEN, GREEN_HOVER)
            self.action_btn.config(text="BẬT LẠI WINDOWS UPDATE", bg=GREEN)

        else:  # STATE_PARTIAL
            self.dot.itemconfig(self.dot_item, fill=AMBER)
            self.status_label.config(text="KHÓA MỘT PHẦN", fg=AMBER)
            self.status_desc.config(text="Một phần cấu hình đã bị hoàn tác, Windows Update có thể vẫn hoạt động")
            self.btn_colors = (RED, RED_HOVER)
            self.action_btn.config(text="TẮT HOÀN TOÀN WINDOWS UPDATE", bg=RED)

    # ------------------------------------------------------------------
    # Xử lý bật / tắt
    # ------------------------------------------------------------------
    def toggle_update(self):
        """Thực hiện khóa/mở khóa triệt để (Dịch vụ + Registry)"""
        if self.busy:
            return

        # Đang tắt hoàn toàn thì bật lại, còn lại (bật hoặc khóa một phần) thì tắt
        should_enable = (self.state == STATE_DISABLED)

        self.set_busy(True)
        success = enable_windows_update() if should_enable else disable_windows_update()
        self.set_busy(False)

        self.update_ui_status()

        # Chỉ hỏi khởi động lại khi thực hiện thành công
        if success:
            if should_enable:
                msg = "Đã BẬT LẠI Windows Update!\n\nBạn có muốn khởi động lại máy ngay để hoàn tất quá trình không?"
            else:
                msg = "Đã TẮT Windows Update!\n\nBạn có muốn khởi động lại máy ngay để áp dụng thay đổi không?"

            if messagebox.askyesno("Thành công", msg):
                restart_computer()
        else:
            action = "bật lại" if should_enable else "tắt hoàn toàn"
            messagebox.showerror(
                "Thất bại",
                f"Không thể {action} Windows Update.\nHãy kiểm tra quyền Administrator và thử lại."
            )

