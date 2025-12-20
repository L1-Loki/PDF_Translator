@echo off
chcp 65001 >nul
echo ====================================
echo ĐÓNG GÓI ỨNG DỤNG THÀNH FILE EXE
echo ====================================
echo.

echo [1/3] Đang kiểm tra và cài đặt thư viện...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo [2/3] Đang build file exe với PyInstaller...
echo Vui lòng đợi 2-3 phút...
echo.

python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "PDF_Translator" ^
    --icon="assets\Loki.ico" ^
    --add-data "translator.py;." ^
    --add-data "pdf_handler.py;." ^
    --add-data "assets\Loki.png;assets" ^
    --hidden-import "deep_translator" ^
    --hidden-import "fitz" ^
    --hidden-import "PIL" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "PIL.ImageDraw" ^
    --collect-all "deep_translator" ^
    --collect-all "pystray" ^
    main_app.py

echo.
echo [3/3] Dọn dẹp file tạm...
if exist build rmdir /s /q build
if exist PDF_Translator.spec del PDF_Translator.spec

echo.
echo ====================================
echo ✅ BUILD HOÀN TẤT!
echo ====================================
echo.
echo 📦 File exe: dist\PDF_Translator.exe
echo 📝 Kích thước: 
dir dist\PDF_Translator.exe | find "PDF_Translator.exe"
echo.
echo 💡 Hướng dẫn:
echo - Copy file PDF_Translator.exe sang máy khác để chạy
echo - Không cần cài Python hay thư viện gì thêm
echo - Hỗ trợ Windows 7/8/10/11 (64-bit)
echo.
pause
