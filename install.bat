@echo off
chcp 65001 >nul
echo ====================================
echo CÀI ĐẶT ỨNG DỤNG DỊCH PDF
echo ====================================
echo.

echo Đang kiểm tra Python...
python --version
echo.

echo Đang nâng cấp pip...
python -m pip install --upgrade pip
echo.

echo Đang cài đặt các thư viện cần thiết...
python -m pip install -r requirements.txt

echo.
echo ====================================
echo ✅ CÀI ĐẶT HOÀN TẤT!
echo ====================================
echo.
echo 💡 Để chạy ứng dụng:
echo   - Double-click file run.bat
echo   - Hoặc gõ lệnh: python main_app.py
echo.
echo 📦 Để build file .exe:
echo   - Chạy: build_exe.bat
echo.
pause
