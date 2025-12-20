@echo off
echo ====================================
echo KHOI DONG UNG DUNG DICH PDF
echo ====================================
echo.

echo Dang khoi dong...
echo.

python main_app.py
@REM python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo LOI: Khong the chay ung dung!
    echo Hay dam bao da cai dat Python va cac thu vien.
    echo Chay file install.bat de cai dat.
    echo.
)

pause
