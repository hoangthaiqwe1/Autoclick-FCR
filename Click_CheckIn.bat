@echo off
title FE Credit - CHECK IN NOW
color 0A
cd /d "%~dp0"
echo ============================================
echo    DANG CHECK-IN...
echo ============================================
echo.
python auto_checkin.py checkin
echo.
echo Done! Cua so se dong sau 5 giay...
timeout /t 5
