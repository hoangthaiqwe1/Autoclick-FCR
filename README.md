# FE Credit Auto Check-in/Check-out

Tự động chấm công trên HR Portal FE Credit.

---

## Yêu cầu

- Windows (có sẵn Chrome hoặc Edge)
- Python 3.8+ (đã có sẵn trên máy công ty)
- **Kết nối mạng nội bộ FE Credit** (HR Portal chỉ truy cập được từ mạng công ty)

**Không cần cài thêm thư viện** — script chỉ dùng thư viện có sẵn của Python (socket, json, urllib).

---

## Hướng dẫn sử dụng

### Bước 1: Clone code

```
git clone https://github.com/hoangthaiqwe1/Autoclick-FCR.git
cd Autoclick-FCR
```

### Bước 2: Tạo file cấu hình `.env`

```
copy .env.example .env
```

Mở file `.env` và sửa thông tin:

```
HR_PORTAL_URL=https://hrportal.fecredit.com.vn/work-attendance
HR_USERNAME=your.email@fecredit.com.vn
HR_PASSWORD=your_password_here

CHECKIN_HOUR=8
CHECKIN_MINUTE=0
CHECKOUT_HOUR=20
CHECKOUT_MINUTE=0
```

| Biến | Ý nghĩa |
|------|---------|
| `HR_USERNAME` | Email đăng nhập FE Credit |
| `HR_PASSWORD` | Mật khẩu (3 tháng đổi 1 lần, cập nhật lại file này) |
| `CHECKOUT_HOUR` | Giờ check-out mặc định nếu không nhập |
| `CHECKOUT_MINUTE` | Phút check-out mặc định |

### Bước 3: Chạy

**Double-click** file `Run_Portal_Checkin.bat`

Hoặc mở CMD:

```
cd "C:\DEV\Auto click"
python Run_Portal_Checkin.py
```

### Bước 4: Lần đầu tiên chạy

1. Chrome mở trang HR Portal
2. Chuyển sang Microsoft Login
3. **Xác thực Face Auth trên điện thoại** (lần đầu hoặc khi session hết hạn)
4. Login xong → script tự check-in (hoặc ghi nhận đã check-in)
5. Hiển thị giờ check-in thực từ API
6. Hỏi giờ check-out (30 giây để nhập, không nhập → mặc định 20:00)
7. Chờ đến giờ → reload page → login lại nếu cần → check-out
8. Hoàn tất

---

## Cập nhật mật khẩu

Mỗi 3 tháng khi đổi mật khẩu, mở file `.env` sửa dòng:

```
HR_PASSWORD=mat_khau_moi
```

---

## Các file trong project

| File | Mô tả |
|------|--------|
| `Run_Portal_Checkin.bat` | Double-click để chạy (thủ công) |
| `Run_Portal_Checkin.py` | Script chính — login, check-in, chờ, check-out |
| `auto_schedule.py` | Script chạy theo Task Scheduler (tự động mỗi ngày) |
| `.env` | Cấu hình tài khoản (không push lên git) |
| `.env.example` | File mẫu cấu hình |
| `auto_checkin.log` | Log lịch sử hoạt động |
| `last_checkin.txt` | Ghi nhận check-in hôm nay |
| `chrome_profile/` | Session Chrome (giữ login, không push) |
| `setup_task.bat` | Cài Task Scheduler tự động chạy mỗi sáng |
| `remove_task.bat` | Gỡ Task Scheduler |

---

## Lưu ý quan trọng

- **Không đóng cửa sổ console** khi script đang chờ check-out
- **Không đóng Chrome** — script cần Chrome để gọi API
- Script giữ session bằng keep-alive mỗi 5 phút → giảm số lần Face Auth
- Máy shutdown lúc 22h (policy) → script đã check-out trước đó
- File `.env` chứa mật khẩu → **không push lên GitHub**
- Chỉ hoạt động khi kết nối **mạng nội bộ FE Credit**
