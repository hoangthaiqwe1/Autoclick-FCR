@echo off
echo Dang xoa task FECredit_AutoCheckin...
schtasks /delete /tn "FECredit_AutoCheckin" /f
echo Done!
pause
