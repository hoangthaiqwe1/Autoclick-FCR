@echo off
title Cai dat Task Scheduler - Auto Cham Cong
color 0A
echo ============================================
echo   CAI DAT TU DONG CHAM CONG 8H SANG
echo ============================================
echo.

:: Lay duong dan hien tai
set SCRIPT_DIR=%~dp0

:: Tao task chay luc 7:55 moi ngay (Thu 2 - Thu 6)
schtasks /create /tn "FECredit_AutoCheckin" /tr "python \"%SCRIPT_DIR%auto_schedule.py\"" /sc weekly /d MON,TUE,WED,THU,FRI /st 07:55 /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Da cai dat thanh cong!
    echo.
    echo     Task: FECredit_AutoCheckin
    echo     Lich: 07:55 sang, Thu 2 - Thu 6
    echo     Script: %SCRIPT_DIR%auto_schedule.py
    echo.
    echo     May tinh phai BAT truoc 8h.
    echo.
) else (
    echo.
    echo [ERROR] Khong tao duoc task!
    echo Thu chay file nay voi quyen Administrator.
    echo.
)

pause
