# FE Credit Auto Check-in/Check-out

Tự động chấm công trên HR Portal FE Credit.

## Có 2 phiên bản

| Phiên bản | File | Yêu cầu |
|-----------|------|----------|
| **PowerShell** (khuyên dùng) | `Run_Portal_Checkin.ps1` | Không cần cài gì thêm |
| Python | `Run_Portal_Checkin.py` | Cần cài Python + thư viện |

---

## Hướng dẫn sử dụng (PowerShell - Khuyên dùng)

### Bước 1: Clone code

```
git clone https://github.com/hoangthaiqwe1/Autoclick-FCR.git
cd Autoclick-FCR
```

### Bước 2: Tạo file cấu hình `.env`

Copy file mẫu:

```
copy .env.example .env
```

Mở file `.env` và sửa thông tin của bạn:

```
HR_PORTAL_URL=https://hrportal.fecredit.com.vn/work-attendance
HR_USERNAME=your.email@fecredit.com.vn
HR_PASSWORD=your_password_here

CHECKIN_HOUR=8
CHECKIN_MINUTE=0
CHECKOUT_HOUR=20
CHECKOUT_MINUTE=0

HEADLESS=false
```

| Biến | Ý nghĩa |
|------|---------|
| `HR_USERNAME` | Email đăng nhập FE Credit |
| `HR_PASSWORD` | Mật khẩu (đổi mỗi 3 tháng, cập nhật lại file này) |
| `CHECKOUT_HOUR` | Giờ check-out mặc định (nếu không nhập khi chạy) |
| `CHECKOUT_MINUTE` | Phút check-out mặc định |

### Bước 3: Chạy script

**Double-click** file `Run_Checkin_PS.bat`

Hoặc mở PowerShell chạy:

```powershell
powershell -ExecutionPolicy Bypass -File "Run_Portal_Checkin.ps1"
```

### Bước 4: Lần đầu tiên

1. Chrome sẽ mở trang HR Portal
2. Trang chuyển sang Microsoft Login
3. **Xác thực Face Auth trên điện thoại** (chỉ lần đầu hoặc khi session hết hạn)
4. Sau khi login xong, script tự check-in
5. Hỏi bạn giờ check-out (30 giây để nhập, không nhập thì mặc định 20:00)
6. Script chờ đến giờ → tự check-out

### Không cần cài thêm gì

- Phiên bản PowerShell chạy native trên Windows
- Chỉ cần có Chrome hoặc Edge đã cài sẵn
- Không cần Python, không cần pip, không cần thư viện

---

## Hướng dẫn sử dụng (Python - Tùy chọn)

### Yêu cầu

- Python 3.8+
- Các thư viện (nếu mạng cho phép cài):

```
pip install -r requirements.txt
```

**Lưu ý:** Mạng công ty có thể chặn pip (proxy 407). Trong trường hợp đó dùng phiên bản PowerShell.

### Chạy

```
python Run_Portal_Checkin.py
```

---

## Cập nhật mật khẩu

Mỗi 3 tháng khi đổi mật khẩu, sửa file `.env`:

```
HR_PASSWORD=mat_khau_moi
```

Hoặc chạy lệnh (phiên bản Python):

```
python auto_schedule.py password MatKhauMoi123
```

---

## Flow hoạt động

```
Chạy script
    → Mở Chrome (dùng profile riêng để giữ session)
    → Login (Azure AD → Microsoft → Face Auth nếu cần)
    → Check-in (nếu chưa check-in)
    → Hiển thị giờ check-in từ API
    → Hỏi giờ check-out (30s, mặc định 20:00)
    → Chờ đến giờ (keep-alive mỗi 5 phút giữ session)
    → Đến giờ: reload page → login lại nếu cần → Check-out
    → Hoàn tất
```

---

## Lưu ý

- **Không đóng cửa sổ console** khi script đang chờ check-out
- **Không đóng Chrome** — script cần Chrome để gọi API
- Máy tính shutdown lúc 22h (policy công ty) → script đã check-out trước đó nên không ảnh hưởng
- File `.env` chứa mật khẩu → **không push lên GitHub** (đã có trong `.gitignore`)
- Thư mục `chrome_profile/` chứa session → không push lên GitHub

---

## Cấu trúc thư mục

```
Autoclick-FCR/
├── .env.example          # File mẫu cấu hình
├── .env                  # File cấu hình thực (tự tạo, không push)
├── .gitignore
├── Run_Checkin_PS.bat    # Double-click để chạy (PowerShell)
├── Run_Portal_Checkin.ps1  # Script chính (PowerShell)
├── Run_Portal_Checkin.py   # Script chính (Python)
├── auto_schedule.py      # Script chạy theo lịch (Python)
├── auto_checkin.py       # Script cũ (tham khảo)
├── chrome_profile/       # Session Chrome (tự tạo khi chạy)
├── auto_checkin.log      # Log hoạt động
└── last_checkin.txt      # Ghi nhận check-in hôm nay
```
