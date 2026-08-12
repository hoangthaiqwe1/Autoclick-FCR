@echo off
title FE Credit - CHECK OUT NOW
color 0E
cd /d "%~dp0"
echo ============================================
echo    DANG CHECK-OUT...
echo ============================================
echo.
python auto_checkin.py checkout
echo.
echo Done! Cua so se dong sau 5 giay...
timeout /t 5
