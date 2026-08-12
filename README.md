# Auto Check-in FE Credit HR Portal

Tool tự động chấm công trên HR Portal FE Credit.

## Cài đặt

### 1. Cài Python (nếu chưa có)
Download từ: https://www.python.org/downloads/

### 2. Cài dependencies
```bash
cd "Auto click"
pip install -r requirements.txt
```

### 3. Cấu hình
Chỉnh sửa file `.env` để thay đổi:
- Thông tin đăng nhập
- Giờ check-in / check-out

## Sử dụng

### Check-in ngay lập tức
```bash
python auto_checkin.py checkin
```

### Check-out ngay lập tức
```bash
python auto_checkin.py checkout
```

### Chạy tự động theo lịch (để máy chạy cả ngày)
```bash
python auto_checkin.py scheduler
```

## Lưu ý quan trọng

1. **IP Check**: Tool chỉ hoạt động khi bạn đang kết nối mạng công ty hoặc VPN
2. **Chrome**: Cần có Google Chrome cài trên máy
3. **Không tắt máy**: Nếu dùng scheduler, máy cần bật và không sleep
4. **Bảo mật**: KHÔNG chia sẻ file `.env` cho ai

## Chạy khi khởi động Windows (Optional)

1. Nhấn `Win + R`, gõ `shell:startup`
2. Tạo file `auto_checkin.bat` trong thư mục đó với nội dung:
```bat
@echo off
cd "C:\Users\DANGLEHOANGTHAI\Downloads\Auto click"
python auto_checkin.py scheduler
```

## Troubleshooting

- Xem log trong file `auto_checkin.log`
- Nếu login lỗi, thử set `HEADLESS=false` trong `.env` để xem trình duyệt
- Nếu button không tìm thấy, có thể web đã thay đổi giao diện
