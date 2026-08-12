@echo off
title Cai dat Task Scheduler - Auto Cham Cong
color 0A
echo ============================================
echo   CAI DAT TU DONG CHAM CONG 8H SANG
echo ============================================
echo.

:: Tao task chay luc 8:00 moi ngay (Thu 2 - Thu 6)
schtasks /create /tn "FECredit_AutoCheckin" /tr "python \"C:\Users\DANGLEHOANGTHAI\Downloads\Auto click\auto_schedule.py\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:00 /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Da cai dat thanh cong!
    echo.
    echo     Task: FECredit_AutoCheckin
    echo     Lich: 08:00 sang, Thu 2 - Thu 6
    echo     Flow: Check-in luc 8h -> Check-out luc 17:30
    echo.
    echo     May tinh phai BAT va KHONG KHOA MAN HINH
    echo     de script chay duoc.
    echo.
) else (
    echo.
    echo [ERROR] Khong tao duoc task!
    echo Thu chay file nay voi quyen Administrator:
    echo   Click phai -> Run as administrator
    echo.
)

pause
