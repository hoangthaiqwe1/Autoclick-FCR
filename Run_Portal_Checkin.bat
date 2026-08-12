@echo off
title FE Credit - Auto Cham Cong
color 0A
cd /d "%~dp0"

echo ============================================
echo    FE CREDIT - AUTO CHAM CONG
echo    (Khong can cai them thu vien)
echo ============================================
echo.

:: Kiem tra Python
python --version
if errorlevel 1 (
    echo.
    echo [ERROR] Khong tim thay Python!
    echo Vui long cai Python va tick "Add Python to PATH"
    pause
    exit /b
)

echo.
echo [OK] San sang! Dang khoi dong...
echo.

python Run_Portal_Checkin.py

echo.
echo [!] Script da dung. Nhan phim bat ky de dong...
pause
