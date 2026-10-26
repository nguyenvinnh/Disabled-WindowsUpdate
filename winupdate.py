import subprocess
import sys
import os
import ctypes
import winreg

# ===== Hằng số Registry =====
HKLM = winreg.HKEY_LOCAL_MACHINE
WOW64 = winreg.KEY_WOW64_64KEY          # luôn đọc/ghi hive 64-bit
POLICY_AU_KEY = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
SERVICES_KEY = r"SYSTEM\CurrentControlSet\Services"
START_DISABLED = 4                      # Start = 4 nghĩa là Disabled

# Trạng thái trả về
STATE_ENABLED = "enabled"               # chưa khóa gì
STATE_DISABLED = "disabled"             # đã khóa đủ (dịch vụ + registry)
STATE_PARTIAL = "partial"               # chỉ khóa được một phần


def is_admin():
    """Kiểm tra xem script có đang chạy với quyền Administrator hay không"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin_privileges():
    """Tự động mở lại chương trình với quyền Admin nếu chưa có (không hiện cửa sổ CMD)"""
    if not is_admin():
        executable = sys.executable

        # Dùng pythonw.exe để không hiện cửa sổ console khi chạy lại với quyền admin
        pythonw = os.path.join(os.path.dirname(executable), "pythonw.exe")
        if os.path.basename(executable).lower() == "python.exe" and os.path.exists(pythonw):
            executable = pythonw

        params = subprocess.list2cmdline(sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, None, 0
        )
        sys.exit(0)

def run_command(command):
    """Thực thi lệnh CMD ngầm hoàn toàn ẩn cửa sổ console"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1


# ----------------------------------------------------------------------
# Hàm hỗ trợ đọc / ghi Registry
# ----------------------------------------------------------------------
def _read_dword(path, name):
    """Đọc giá trị DWORD trong HKLM, trả về None nếu không tồn tại"""
    try:
        with winreg.OpenKey(HKLM, path, 0, winreg.KEY_READ | WOW64) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except OSError:
        return None

def _write_policy(name, value):
    """Ghi giá trị DWORD vào khóa policy Windows Update\AU"""
    try:
        with winreg.CreateKeyEx(HKLM, POLICY_AU_KEY, 0, winreg.KEY_SET_VALUE | WOW64) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        return True
    except OSError:
        return False

def _delete_policy_value(name):
    """Chỉ xóa đúng giá trị do ứng dụng tạo, không đụng tới các policy khác"""
    try:
        with winreg.OpenKey(HKLM, POLICY_AU_KEY, 0, winreg.KEY_SET_VALUE | WOW64) as key:
            winreg.DeleteValue(key, name)
    except OSError:
        pass  # giá trị/khóa không tồn tại thì coi như đã xóa

def _is_service_disabled(service_name):
    return _read_dword(f"{SERVICES_KEY}\\{service_name}", "Start") == START_DISABLED


# ----------------------------------------------------------------------
# Kiểm tra trạng thái
# ----------------------------------------------------------------------
def get_windows_update_status():
    """
    Xác định trạng thái thực tế dựa trên CẤU HÌNH (không phụ thuộc dịch vụ có đang chạy hay không).
    Trả về (state, details) với:
      state   : STATE_ENABLED / STATE_DISABLED / STATE_PARTIAL
      details : {"service_locked": bool, "policy_locked": bool}
    """
    service_locked = _is_service_disabled("wuauserv")
    policy_locked = _read_dword(POLICY_AU_KEY, "NoAutoUpdate") == 1

    if service_locked and policy_locked:
        state = STATE_DISABLED
    elif not service_locked and not policy_locked:
        state = STATE_ENABLED
    else:
        state = STATE_PARTIAL

    return state, {"service_locked": service_locked, "policy_locked": policy_locked}


# ----------------------------------------------------------------------
# Bật / tắt
# ----------------------------------------------------------------------
def disable_windows_update():
    """Tắt triệt để Windows Update. Trả về True nếu cấu hình đã được khóa đủ"""
    run_command("net stop wuauserv /y")
    run_command("net stop UsoSvc /y")
    run_command("sc config wuauserv start= disabled")
    run_command("sc config UsoSvc start= disabled")
    _write_policy("NoAutoUpdate", 1)
    _write_policy("AUOptions", 2)

    state, _ = get_windows_update_status()
    return state == STATE_DISABLED

def enable_windows_update():
    """Bật lại Windows Update. Trả về True nếu cấu hình đã được mở khóa hoàn toàn"""
    run_command("sc config wuauserv start= demand")
    run_command("sc config UsoSvc start= demand")
    _delete_policy_value("NoAutoUpdate")
    _delete_policy_value("AUOptions")
    run_command("net start wuauserv")
    run_command("net start UsoSvc")

    state, _ = get_windows_update_status()
    return state == STATE_ENABLED

def restart_computer():
    """Khởi động lại máy tính ngay lập tức"""
    run_command("shutdown /r /t 0")

