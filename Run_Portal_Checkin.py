"""
FE Credit Auto Check-in/Check-out - 1 file duy nhat
=====================================================
Double-click -> Login -> Check-in (neu chua) -> Set gio check-out -> Tu dong check-out
"""

import subprocess
import sys
import os
import time
import json
import socket
import urllib.request
import base64
import struct
import random
import threading
from datetime import datetime, timedelta

# ==================== CAU HINH ====================
HR_PORTAL_URL = "https://hrportal.fecredit.com.vn/work-attendance"
HR_USERNAME = "thai.dang.4@fecredit.com.vn"
HR_PASSWORD = "TCBtcb@110411045"

WORK_DURATION_HOURS = 9
WORK_DURATION_MINUTES = 30

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


# === CHECKIN RECORD ===
def already_checked_in_today():
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(CHECKIN_RECORD_FILE, "r") as f:
            return f.read().strip().startswith(today_str)
    except:
        return False

def mark_checked_in():
    try:
        with open(CHECKIN_RECORD_FILE, "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except:
        pass

def get_checkin_time_today():
    try:
        with open(CHECKIN_RECORD_FILE, "r") as f:
            return datetime.strptime(f.read().strip(), "%Y-%m-%d %H:%M:%S")
    except:
        return None


# === CHROME CONTROL ===
def find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

def is_port_open(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        r = s.connect_ex(('127.0.0.1', port))
        s.close()
        return r == 0
    except:
        return False

def start_chrome(url):
    chrome = find_chrome()
    if not chrome:
        log("ERROR: Khong tim thay Chrome!")
        return False
    if is_port_open(CDP_PORT):
        return True
    user_data = os.path.join(SCRIPT_DIR, "chrome_profile")
    subprocess.Popen([chrome, f"--remote-debugging-port={CDP_PORT}", f"--user-data-dir={user_data}", "--no-first-run", "--no-default-browser-check", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        if is_port_open(CDP_PORT):
            return True
        time.sleep(1)
    return False

def cdp_request(endpoint):
    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}{endpoint}"), timeout=10) as resp:
            return json.loads(resp.read().decode())
    except:
        return None

def get_page_tabs():
    return cdp_request("/json")

def ws_send(ws_url, message):
    url = ws_url.replace("ws://", "")
    host_port, path = url.split("/", 1) if "/" in url else (url, "")
    path = "/" + path
    host, port = (host_port.split(":")[0], int(host_port.split(":")[1])) if ":" in host_port else (host_port, 80)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((host, port))
    key = base64.b64encode(random.randbytes(16)).decode()
    sock.send(f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += sock.recv(4096)
    
    payload = message.encode("utf-8")
    frame = bytearray([0x81])
    mask_key = random.randbytes(4)
    ln = len(payload)
    if ln < 126: frame.append(0x80 | ln)
    elif ln < 65536: frame.append(0x80 | 126); frame.extend(struct.pack(">H", ln))
    else: frame.append(0x80 | 127); frame.extend(struct.pack(">Q", ln))
    frame.extend(mask_key)
    frame.extend(bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload)))
    sock.send(frame)
    
    data = sock.recv(65536)
    sock.close()
    if len(data) < 2: return None
    sb = data[1] & 0x7F
    off = 2 if sb < 126 else (4 if sb == 126 else 10)
    try: return json.loads(data[off:].decode("utf-8", errors="ignore"))
    except: return None

def run_js(code):
    tabs = get_page_tabs()
    if not tabs: return None
    tab = next((t for t in tabs if t.get("type") == "page"), tabs[0] if tabs else None)
    if not tab: return None
    ws = tab.get("webSocketDebuggerUrl")
    if not ws: return None
    try: return ws_send(ws, json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":code,"returnByValue":True,"awaitPromise":True}}))
    except: return None


# === LOGIN ===
def wait_and_login():
    for attempt in range(8):
        time.sleep(5)
        tabs = get_page_tabs()
        if not tabs: continue
        url = ""
        for t in tabs:
            if t.get("type") == "page": url = t.get("url", ""); break
        
        log(f"  [{attempt+1}] {url[:70]}")

        if "work-attendance" in url:
            return True

        if "sign-in" in url and "microsoftonline" not in url:
            run_js("""(function(){var b=document.querySelectorAll('button,a');for(var i=0;i<b.length;i++){if(b[i].textContent.indexOf('Azure')!==-1){b[i].click();return;}}})()""")
            time.sleep(8)
            continue

        if "microsoftonline" in url or "login.live" in url:
            # Pick account
            r = run_js("""(function(){var t=document.getElementById('tilesHolder');if(t){var f=t.querySelector('div[tabindex],div.table-row,[data-test-id]');if(f){f.click();return'PICKED';}}var rows=document.querySelectorAll('.table-row,[role="button"]');for(var i=0;i<rows.length;i++){if(rows[i].textContent.indexOf('thai.dang')!==-1||rows[i].textContent.indexOf('fecredit')!==-1){rows[i].click();return'PICKED';}}return'NO';})()""")
            if r and "PICKED" in str(r):
                time.sleep(8)
                tabs = get_page_tabs()
                if tabs:
                    for t in tabs:
                        if t.get("type") == "page": url = t.get("url", ""); break
                    if "work-attendance" in url: return True

            # Email
            for _ in range(10):
                time.sleep(2)
                r = run_js(f"""(function(){{var f=document.querySelector('input[name="loginfmt"],#i0116');if(f){{f.focus();f.value='{HR_USERNAME}';f.dispatchEvent(new Event('input',{{bubbles:true}}));return'OK';}}if(document.querySelector('input[name="passwd"],#i0118'))return'PASS';return'W';}})()""")
                if r and ("'OK'" in str(r) or "PASS" in str(r)): break

            if r and "PASS" not in str(r):
                time.sleep(1)
                run_js("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b)b.click();})()""")

            # Password
            for _ in range(10):
                time.sleep(2)
                r = run_js(f"""(function(){{var f=document.querySelector('input[name="passwd"],#i0118');if(f){{f.focus();f.value='{HR_PASSWORD}';f.dispatchEvent(new Event('input',{{bubbles:true}}));return'OK';}}return'W';}})()""")
                if r and "'OK'" in str(r): break

            time.sleep(1)
            run_js("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b)b.click();})()""")
            time.sleep(6)
            run_js("""(function(){var b=document.getElementById('idSIButton9')||document.querySelector('input[type="submit"]');if(b)b.click();})()""")
            time.sleep(6)
            return True
    return False


# === CHECK-IN / CHECK-OUT ===
def do_checkin():
    log(">>> CHECK-IN")
    r = run_js("""(function(){return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-in',{method:'POST',headers:{'Accept':'application/json','Content-Type':'application/json'},credentials:'include'}).then(function(r){return r.text().then(function(t){return'STATUS:'+r.status+' '+t;});}).catch(function(e){return'ERR:'+e.message;});})()""")
    log(f"  {r}")
    if r and ("STATUS:200" in str(r) or "STATUS:201" in str(r)):
        mark_checked_in()
        log("  CHECK-IN THANH CONG!")
        run_js("window.location.href='https://hrportal.fecredit.com.vn/work-attendance';")
        return True
    return False

def do_checkout():
    log(">>> CHECK-OUT")
    r = run_js("""(function(){return fetch('https://hrportal.fecredit.com.vn/api/v1/employee-attendance/check-out',{method:'POST',headers:{'Accept':'application/json','Content-Type':'application/json'},credentials:'include'}).then(function(r){return r.text().then(function(t){return'STATUS:'+r.status+' '+t;});}).catch(function(e){return'ERR:'+e.message;});})()""")
    log(f"  {r}")
    if r and ("STATUS:200" in str(r) or "STATUS:201" in str(r)):
        log("  CHECK-OUT THANH CONG!")
        run_js("window.location.href='https://hrportal.fecredit.com.vn/work-attendance';")
        return True
    return False


# === INPUT WITH TIMEOUT ===
def input_with_timeout(prompt, timeout=20):
    """Hoi input, neu khong nhap trong timeout giay thi tra ve None."""
    result = [None]
    
    def ask():
        try:
            result[0] = input(prompt)
        except:
            pass
    
    t = threading.Thread(target=ask, daemon=True)
    t.start()
    t.join(timeout)
    
    if t.is_alive():
        print(f"\n  (Het {timeout}s, dung mac dinh)")
        return None
    return result[0]


# === MAIN ===
def main():
    print("")
    print("=" * 50)
    print("   FE CREDIT - AUTO CHAM CONG")
    print("=" * 50)
    print("")

    # Buoc 1: Mo Chrome va Login
    log("Buoc 1: Mo Chrome va login...")
    if not start_chrome(HR_PORTAL_URL):
        log("Khong mo duoc Chrome!")
        input("Nhan Enter de dong...")
        return

    if not wait_and_login():
        log("Khong login duoc!")
        input("Nhan Enter de dong...")
        return

    log("LOGIN THANH CONG!")
    print("")

    # Buoc 2: Kiem tra check-in
    log("Buoc 2: Kiem tra check-in...")
    if already_checked_in_today():
        checkin_time = get_checkin_time_today()
        log(f"  Da check-in luc {checkin_time.strftime('%H:%M') if checkin_time else '?'}")
    else:
        log("  Chua check-in, dang check-in...")
        time.sleep(2)
        do_checkin()
        checkin_time = datetime.now()

    print("")

    # Buoc 3: Set gio check-out (20 giay de nhap, khong nhap thi mac dinh)
    checkin_time = get_checkin_time_today() or datetime.now()
    default_checkout = checkin_time + timedelta(hours=WORK_DURATION_HOURS, minutes=WORK_DURATION_MINUTES)

    print(f"  Check-in luc:         {checkin_time.strftime('%H:%M')}")
    print(f"  Check-out mac dinh:   {default_checkout.strftime('%H:%M')} (sau {WORK_DURATION_HOURS}h{WORK_DURATION_MINUTES:02d})")
    print("")

    user_input = input_with_timeout("  Nhap gio check-out (VD: 17:30) [30s]: ", 30)

    if user_input and user_input.strip():
        try:
            parts = user_input.strip().replace("h", ":").replace("H", ":").split(":")
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if h < 0 or h > 23 or m < 0 or m > 59:
                raise ValueError("Gio khong hop le")
            checkout_time = datetime.now().replace(hour=h, minute=m, second=0)
            # Neu gio checkout da qua (VD nhap 8:00 ma gio la 17h) -> hieu la ngay mai
            if checkout_time <= datetime.now():
                checkout_time += timedelta(days=1)
            log(f"  Set check-out: {checkout_time.strftime('%H:%M')}")
        except:
            log(f"  Gio khong hop le! Dung mac dinh.")
            checkout_time = default_checkout
    else:
        checkout_time = default_checkout
        log(f"  Dung mac dinh: {checkout_time.strftime('%H:%M')}")

    print("")
    print("=" * 50)
    log(f"  Se check-out luc: {checkout_time.strftime('%H:%M')}")
    print("  KHONG DONG CUA SO NAY!")
    print("=" * 50)
    print("")

    # Buoc 4: Doi den gio check-out
    while True:
        now = datetime.now()
        remaining = (checkout_time - now).total_seconds()

        if remaining <= 0:
            log("DEN GIO CHECK-OUT!")
            time.sleep(2)
            do_checkout()
            print("")
            log("=== HOAN TAT! ===")
            input("\nNhan Enter de dong...")
            return

        hours_left = int(remaining // 3600)
        mins_left = int((remaining % 3600) // 60)
        log(f"  Con {hours_left}h {mins_left}p -> check-out luc {checkout_time.strftime('%H:%M')}")
        
        # Gan den gio thi check thuong xuyen hon
        if remaining < 60:
            time.sleep(10)
        elif remaining < 300:
            time.sleep(30)
        else:
            time.sleep(300)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            cmd = sys.argv[1].lower()
            if cmd == "checkin":
                start_chrome(HR_PORTAL_URL)
                wait_and_login()
                do_checkin()
            elif cmd == "checkout":
                start_chrome(HR_PORTAL_URL)
                wait_and_login()
                do_checkout()
        else:
            main()
    except KeyboardInterrupt:
        log("\nDa dung.")
    except Exception as e:
        log(f"LOI: {e}")
        import traceback
        traceback.print_exc()
        input("\nNhan Enter de dong...")
