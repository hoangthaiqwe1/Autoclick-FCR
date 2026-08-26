"""
FE Credit Auto Schedule - Chay tu dong khong can input
=======================================================
File nay duoc Task Scheduler goi luc 8h sang moi ngay.
Tu dong: Check-in -> Doi 9h30 -> Check-out
"""

import subprocess
import sys
import os
import time
import json
import socket
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# ==================== CAU HINH ====================
# Doc tu file .env - khi doi mat khau chi can sua file .env
def load_env_file():
    """Doc file .env thu cong (khong can thu vien dotenv)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

load_env_file()

HR_PORTAL_URL = os.getenv("HR_PORTAL_URL", "https://hrportal.fecredit.com.vn/work-attendance")
HR_USERNAME = os.getenv("HR_USERNAME", "")
HR_PASSWORD = os.getenv("HR_PASSWORD", "")

# Gio check-out mac dinh (lay tu .env, khong co thi 20:00)
CHECKOUT_HOUR = int(os.getenv("CHECKOUT_HOUR", 20))
CHECKOUT_MINUTE = int(os.getenv("CHECKOUT_MINUTE", 0))

# Chrome path
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

CDP_PORT = 9222
# ==================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "auto_checkin.log")
CHECKIN_RECORD_FILE = os.path.join(SCRIPT_DIR, "last_checkin.txt")


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass


def already_checked_in_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CHECKIN_RECORD_FILE, "r") as f:
            content = f.read().strip()
            return content.startswith(today_str)
    except:
        return False


def mark_checked_in():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(CHECKIN_RECORD_FILE, "w") as f:
            f.write(now_str)
    except:
        pass


def get_checkin_time_today():
    try:
        with open(CHECKIN_RECORD_FILE, "r") as f:
            content = f.read().strip()
            return datetime.strptime(content, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def find_chrome():
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def is_port_open(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


def start_chrome(url):
    chrome_path = find_chrome()
    if not chrome_path:
        log("ERROR: Khong tim thay Chrome!")
        return False

    user_data = os.path.join(SCRIPT_DIR, "chrome_profile")

    if is_port_open(CDP_PORT):
        log(f"Chrome da chay tren port {CDP_PORT}")
        return True

    cmd = [
        chrome_path,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={user_data}",
        "--no-first-run",
        "--no-default-browser-check",
        url
    ]

    log("Dang mo Chrome...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for i in range(30):
        if is_port_open(CDP_PORT):
            log("Chrome da san sang!")
            return True
        time.sleep(1)

    log("ERROR: Chrome khong khoi dong duoc")
    return False


def cdp_request(endpoint):
    try:
        url = f"http://127.0.0.1:{CDP_PORT}{endpoint}"
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(url)
        with opener.open(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"CDP error: {e}")
        return None


def get_page_tabs():
    return cdp_request("/json")


def simple_websocket_send(ws_url, message):
    import base64
    import struct
    import random

    url = ws_url.replace("ws://", "")
    host_port, path = url.split("/", 1) if "/" in url else (url, "")
    path = "/" + path

    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host = host_port
        port = 80

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((host, port))

    key = base64.b64encode(random.randbytes(16)).decode()
    handshake = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    )
    sock.send(handshake.encode())

    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)

    payload = message.encode("utf-8")
    frame = bytearray()
    frame.append(0x81)

    mask_key = random.randbytes(4)
    length = len(payload)

    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack(">Q", length))

    frame.extend(mask_key)
    masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    frame.extend(masked)

    sock.send(frame)

    data = sock.recv(65536)

    if len(data) < 2:
        sock.close()
        return None

    second_byte = data[1] & 0x7F
    offset = 2
    if second_byte == 126:
        offset = 4
    elif second_byte == 127:
        offset = 10

    payload_data = data[offset:]
    sock.close()

    try:
        return json.loads(payload_data.decode("utf-8", errors="ignore"))
    except:
        return payload_data.decode("utf-8", errors="ignore")


def run_js_in_tab(js_code):
    tabs = get_page_tabs()
    if not tabs:
        return None

    target_tab = None
    for tab in tabs:
        if "fecredit" in tab.get("url", "") or "microsoftonline" in tab.get("url", "") or tab.get("type") == "page":
            target_tab = tab
            break

    if not target_tab and tabs:
        target_tab = tabs[0]

    if not target_tab:
        return None

    ws_url = target_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return None

    command = json.dumps({
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True
        }
    })

    try:
        return simple_websocket_send(ws_url, command)
    except Exception as e:
        log(f"JS error: {e}")
        return None


def navigate_to(url):
    tabs = get_page_tabs()
    if not tabs:
        return False
    target_tab = None
    for tab in tabs:
        if tab.get("type") == "page":
            target_tab = tab
            break
    if not target_tab:
        return False
    ws_url = target_tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return False
    command = json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}})
    try:
        simple_websocket_send(ws_url, command)
        return True
    except:
        return False


def wait_and_check_login():
    """Login tu dong."""
    for attempt in range(8):
        time.sleep(5)
        tabs = get_page_tabs()
        if not tabs:
            log(f"  Lan {attempt+1}: Khong thay tab...")
            continue

        current_url = ""
        for tab in tabs:
            if tab.get("type") == "page":
                current_url = tab.get("url", "")
                break

        log(f"  Lan {attempt+1} - URL: {current_url[:60]}")

        if "work-attendance" in current_url:
            log("  Da login xong!")
            return True

        # Trang sign-in FE Credit -> click Azure AD
        if "sign-in" in current_url and "microsoftonline" not in current_url:
            log("  Click Azure AD...")
            js = """
            (function() {
                var buttons = document.querySelectorAll('button, a');
                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].textContent || '';
                    if (text.indexOf('Azure') !== -1 || text.indexOf('ng nh') !== -1) {
                        buttons[i].click();
                        return 'OK';
                    }
                }
                return 'NOT_FOUND';
            })()
            """
            run_js_in_tab(js)
            time.sleep(8)
            continue

        # Trang Microsoft login
        if "microsoftonline" in current_url or "login.live" in current_url:
            # Thu pick account truoc
            js_pick = f"""
            (function() {{
                var tiles = document.getElementById('tilesHolder');
                if (tiles) {{
                    var first = tiles.querySelector('div[tabindex], .table-row, div[data-test-id]');
                    if (first) {{ first.click(); return 'PICKED'; }}
                }}
                var rows = document.querySelectorAll('.table-row');
                if (rows.length > 0) {{ rows[0].click(); return 'PICKED_ROW'; }}
                var clickables = document.querySelectorAll('[role="button"], [tabindex="0"]');
                for (var i = 0; i < clickables.length; i++) {{
                    if (clickables[i].textContent.indexOf('thai.dang') !== -1) {{
                        clickables[i].click();
                        return 'PICKED_CLICKABLE';
                    }}
                }}
                return 'NO_PICKER';
            }})()
            """
            result = run_js_in_tab(js_pick)
            log(f"  Pick account: {result}")

            if result and "PICKED" in str(result):
                time.sleep(8)
                # Kiem tra da login xong chua
                tabs = get_page_tabs()
                if tabs:
                    for tab in tabs:
                        if tab.get("type") == "page":
                            current_url = tab.get("url", "")
                            break
                    if "work-attendance" in current_url:
                        log("  Login xong sau pick account!")
                        return True

            # Thu nhap email
            email_ok = False
            for retry in range(10):
                time.sleep(2)
                js_email = f"""
                (function() {{
                    var f = document.querySelector('input[name="loginfmt"]') || document.querySelector('#i0116');
                    if (f) {{ f.focus(); f.value = '{HR_USERNAME}'; f.dispatchEvent(new Event('input', {{bubbles:true}})); return 'OK'; }}
                    var p = document.querySelector('input[name="passwd"]') || document.querySelector('#i0118');
                    if (p) return 'AT_PASS';
                    return 'WAIT';
                }})()
                """
                r = run_js_in_tab(js_email)
                rs = str(r)
                if "'OK'" in rs:
                    email_ok = True
                    break
                elif "AT_PASS" in rs:
                    email_ok = True
                    break
                    
            if not email_ok:
                continue

            # Click Next
            if "AT_PASS" not in str(r):
                time.sleep(1)
                run_js_in_tab("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b){b.click();return 'OK';}return 'NO';})()""")

            # Nhap password
            for retry in range(10):
                time.sleep(2)
                js_pass = f"""
                (function() {{
                    var f = document.querySelector('input[name="passwd"]') || document.querySelector('#i0118');
                    if (f) {{ f.focus(); f.value = '{HR_PASSWORD}'; f.dispatchEvent(new Event('input', {{bubbles:true}})); return 'OK'; }}
                    return 'WAIT';
                }})()
                """
                r = run_js_in_tab(js_pass)
                if "'OK'" in str(r):
                    break

            # Click Sign in
            time.sleep(1)
            run_js_in_tab("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b){b.click();return 'OK';}return 'NO';})()""")
            time.sleep(6)

            # Kiem tra MFA - cho toi da 2 phut de user approve tren dien thoai
            for mfa_wait in range(24):  # 24 x 5s = 120s = 2 phut
                tabs = get_page_tabs()
                if tabs:
                    current_url = ""
                    for t in tabs:
                        if t.get("type") == "page": current_url = t.get("url", ""); break
                    if "work-attendance" in current_url or "hrportal" in current_url:
                        log("  Login thanh cong!")
                        return True
                    if "microsoftonline" in current_url:
                        # Thu click Stay signed in
                        run_js_in_tab("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b){b.click();return 'OK';}return 'NO';})()""")
                        if mfa_wait == 0:
                            log("  Dang cho xac thuc MFA (approve tren dien thoai)...")
                        time.sleep(5)
                        continue
                    else:
                        log("  Login xong!")
                        return True
                time.sleep(5)

            log("  Het thoi gian cho MFA (2 phut)")
            return True

    log("  Khong the login!")
    return False


def get_today_attendance():
    """Lay thong tin cham cong hom nay tu API HR Portal."""
    js = """
    (function() {
        return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/account-info', {
            method: 'GET',
            headers: {'Accept': 'application/json'},
            credentials: 'include'
        }).then(function(r) { return r.text(); })
        .catch(function(e) { return 'ERR:' + e.message; });
    })()
    """
    r = run_js_in_tab(js)
    if r:
        try:
            value = r.get("result", {}).get("result", {}).get("value", "")
            if value and not value.startswith("ERR"):
                data = json.loads(value)
                if isinstance(data, dict) and data.get("status"):
                    info = data.get("data", {})
                    checkin_raw = info.get("checkInTime")
                    checkout_raw = info.get("checkOutTime")
                    checkin_display = ""
                    checkout_display = ""
                    if checkin_raw:
                        try:
                            checkin_display = datetime.strptime(checkin_raw[:19], "%Y-%m-%dT%H:%M:%S").strftime("%H:%M:%S")
                        except:
                            checkin_display = checkin_raw
                    if checkout_raw:
                        try:
                            checkout_display = datetime.strptime(checkout_raw[:19], "%Y-%m-%dT%H:%M:%S").strftime("%H:%M:%S")
                        except:
                            checkout_display = checkout_raw
                    return {
                        "checkin": checkin_display,
                        "checkout": checkout_display,
                        "status": info.get("status")
                    }
        except:
            pass
    return None


def do_checkin():
    if datetime.now().weekday() >= 5:
        log("Cuoi tuan - bo qua")
        return
    if already_checked_in_today():
        log("Da check-in hom nay roi.")
        return

    log("=== CHECK-IN ===")
    if not start_chrome(HR_PORTAL_URL):
        return

    wait_and_check_login()
    time.sleep(3)

    # Dam bao dang o trang work-attendance truoc khi goi API
    navigate_to(HR_PORTAL_URL)
    time.sleep(5)

    js = """
    (function() {
        return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-in', {
            method: 'POST',
            headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
            credentials: 'include'
        }).then(function(r) { return r.text().then(function(t) { return 'STATUS:' + r.status + ' ' + t; }); })
        .catch(function(e) { return 'ERROR:' + e.message; });
    })()
    """
    result = run_js_in_tab(js)
    log(f"CHECK-IN: {result}")

    result_str = str(result)
    if "STATUS:200" in result_str or "STATUS:201" in result_str:
        mark_checked_in()
        log("CHECK-IN THANH CONG!")
        time.sleep(2)
        run_js_in_tab("window.location.href='https://hrportal.fecredit.com.vn/work-attendance';")
    elif "CHECKIN_FAILED" in result_str or '"code":"11"' in result_str:
        mark_checked_in()
        log("Da check-in truoc do roi (API tra CHECKIN_FAILED)")


def do_checkout():
    if datetime.now().weekday() >= 5:
        log("Cuoi tuan - bo qua")
        return

    log("=== CHECK-OUT ===")
    if not start_chrome(HR_PORTAL_URL):
        return

    wait_and_check_login()
    time.sleep(3)

    # Dam bao dang o trang work-attendance truoc khi goi API
    navigate_to(HR_PORTAL_URL)
    time.sleep(5)

    js = """
    (function() {
        return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-out', {
            method: 'POST',
            headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
            credentials: 'include'
        }).then(function(r) { return r.text().then(function(t) { return 'STATUS:' + r.status + ' ' + t; }); })
        .catch(function(e) { return 'ERROR:' + e.message; });
    })()
    """
    result = run_js_in_tab(js)
    log(f"CHECK-OUT: {result}")

    if result and ("STATUS:200" in str(result) or "STATUS:201" in str(result)):
        log("CHECK-OUT THANH CONG!")
        time.sleep(2)
        run_js_in_tab("window.location.href='https://hrportal.fecredit.com.vn/work-attendance';")


def close_chrome_gracefully():
    """Dong Chrome sach se de bao toan cookie/session."""
    log("Dang dong Chrome...")
    try:
        tabs = get_page_tabs()
        if tabs:
            for tab in tabs:
                ws_url = tab.get("webSocketDebuggerUrl")
                if ws_url:
                    try:
                        command = json.dumps({"id": 1, "method": "Browser.close"})
                        simple_websocket_send(ws_url, command)
                        log("Chrome da dong qua CDP.")
                        time.sleep(3)
                        return True
                    except:
                        pass
    except:
        pass

    # Fallback: dung taskkill nhung cho Chrome tu save truoc
    try:
        # Gui WM_CLOSE thay vi force kill
        subprocess.run(
            ["taskkill", "/IM", "chrome.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10
        )
        time.sleep(3)
        log("Chrome da dong qua taskkill.")
        return True
    except:
        pass

    log("Khong the dong Chrome.")
    return False


def main():
    """Chay tu dong: check-in -> doi 9h30 -> check-out."""
    today = datetime.now()

    if today.weekday() >= 5:
        log("Cuoi tuan - khong cham cong.")
        return

    log("")
    log("=" * 50)
    log("   FE CREDIT - AUTO CHAM CONG (Scheduled)")
    log(f"   {today.strftime('%d/%m/%Y %H:%M:%S')}")
    log("=" * 50)

    # Check-in
    do_checkin()
    checkin_time = get_checkin_time_today() or datetime.now()

    # Lay gio check-in thuc tu API
    time.sleep(3)
    attendance = get_today_attendance()
    checkin_display = ""
    if attendance and attendance.get("checkin"):
        checkin_display = attendance["checkin"]
        log(f"   Check-in (API): {checkin_display}")
    else:
        log(f"   Check-in (local): {checkin_time.strftime('%H:%M')}")

    # Gio check-out co dinh (lay tu .env, mac dinh 20:00)
    checkout_time = datetime.now().replace(hour=CHECKOUT_HOUR, minute=CHECKOUT_MINUTE, second=0, microsecond=0)
    if checkout_time <= datetime.now():
        checkout_time += timedelta(days=1)
    log(f"   Check-in:  {checkin_time.strftime('%H:%M')}")
    log(f"   Check-out: {checkout_time.strftime('%H:%M')}")
    log("")

    # Doi den gio check-out
    while True:
        now = datetime.now()
        remaining = (checkout_time - now).total_seconds()

        if remaining <= 0:
            log("DEN GIO CHECK-OUT!")
            do_checkout()
            time.sleep(5)
            # Dong Chrome sach se de giu session cho ngay mai
            close_chrome_gracefully()
            log("HOAN TAT!")
            return

        hours_left = int(remaining // 3600)
        mins_left = int((remaining % 3600) // 60)
        if int(remaining) % 600 < 35:
            log(f"   Con {hours_left}h {mins_left}p -> check-out luc {checkout_time.strftime('%H:%M')}")

        time.sleep(30)


if __name__ == "__main__":
    try:
        # Ho tro cap nhat mat khau nhanh qua command line
        if len(sys.argv) > 1 and sys.argv[1] == "password":
            env_path = os.path.join(SCRIPT_DIR, ".env")
            if len(sys.argv) > 2:
                new_pass = sys.argv[2]
            else:
                import getpass
                new_pass = getpass.getpass("Nhap mat khau moi: ")

            # Doc file .env hien tai
            lines = []
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except:
                pass

            # Cap nhat dong HR_PASSWORD
            found = False
            for i, line in enumerate(lines):
                if line.startswith("HR_PASSWORD"):
                    lines[i] = f"HR_PASSWORD={new_pass}\n"
                    found = True
                    break
            if not found:
                lines.append(f"HR_PASSWORD={new_pass}\n")

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            print(f"Da cap nhat mat khau trong .env!")
            print(f"Mat khau moi: {'*' * (len(new_pass) - 3)}{new_pass[-3:]}")
            sys.exit(0)

        main()
    except KeyboardInterrupt:
        log("Da dung.")
    except Exception as e:
        log(f"LOI: {e}")
        import traceback
        traceback.print_exc()
