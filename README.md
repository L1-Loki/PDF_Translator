# Ứng Dụng Dịch PDF English - Vietnamese

Ứng dụng dịch thuật PDF từ tiếng Anh sang tiếng Việt với khả năng giữ nguyên định dạng của file PDF gốc. Hỗ trợ xử lý PDF lớn lên đến 1000+ trang.

## Tính Năng

✨ **Các tính năng chính:**

- ✅ Dịch từ English sang Vietnamese
- ✅ Giữ nguyên định dạng PDF (font size, màu sắc, vị trí)
- ✅ Xử lý được file PDF lớn (1000+ trang)
- ✅ Giao diện đồ họa thân thiện, dễ sử dụng
- ✅ Hiển thị tiến trình dịch real-time
- ✅ Log chi tiết quá trình xử lý

## Yêu Cầu Hệ Thống

- **Hệ điều hành:** Windows 10/11
- **Python:** 3.8 trở lên
- **Kết nối Internet:** Cần thiết để sử dụng dịch vụ Google Translate

## Cài Đặt

### Bước 1: Cài đặt Python

Nếu chưa có Python, tải và cài đặt từ [python.org](https://www.python.org/downloads/)

Lưu ý: Trong quá trình cài đặt, nhớ check vào "Add Python to PATH"

### Bước 2: Tải mã nguồn

```bash
# Clone hoặc download mã nguồn về máy
git clone https://github.com/L1-Loki/PDF_Translator.git
```

### Bước 3: Cài đặt thư viện

**Cách 1: Sử dụng file .bat (Đơn giản nhất)**

- Double-click file `install.bat`
- Đợi quá trình cài đặt hoàn tất

**Cách 2: Dùng PowerShell**

```powershell
.\install.bat
# Hoặc
pip install -r requirements.txt
```

**Lưu ý cho PowerShell:** Phải thêm `.\` trước tên file .bat

## Cách Sử Dụng

### 🎯 Phương pháp 1: Dùng file EXE (KHUYẾN NGHỊ)

**Bước 1: Build file EXE lần đầu**

```powershell
.\build_exe.bat
```

Quá trình này chỉ cần chạy 1 lần, sẽ tạo file `PDF_Translator.exe` trong thư mục `dist/`

**Bước 2: Chạy ứng dụng**

- Double-click file `dist/PDF_Translator.exe`
- Không cần cài Python hay thư viện gì!

### 🐍 Phương pháp 2: Chạy bằng Python

**Cách 1: Double-click**

- Double-click file `run.bat`

**Cách 2: Dùng PowerShell**

```powershell
.\run.bat
# Hoặc
python main_app.py
```

### Các bước dịch PDF:

1. **Chọn file PDF gốc:**

   - Click nút "Chọn File"
   - Chọn file PDF tiếng Anh cần dịch
   - Ứng dụng sẽ hiển thị thông tin về file (số trang, kích thước)

2. **Chọn vị trí lưu:**

   - Click nút "Chọn Vị Trí"
   - Chọn nơi muốn lưu file PDF đã dịch
   - (Mặc định sẽ lưu cùng thư mục với file gốc, tên file có thêm "\_translated")

3. **Bắt đầu dịch:**
   - Click nút "BẮT ĐẦU DỊCH"
   - Xác nhận trong hộp thoại
   - Đợi quá trình xử lý hoàn tất

### Quá trình dịch gồm 3 giai đoạn:

1. **Đọc PDF (0-33%):** Trích xuất văn bản và định dạng từ PDF gốc
2. **Dịch văn bản (33-66%):** Dịch từng khối văn bản sang tiếng Việt
3. **Tạo PDF mới (66-100%):** Tạo file PDF mới với văn bản đã dịch

## Lưu Ý Quan Trọng

⚠️ **Thời gian xử lý:**

- File nhỏ (< 50 trang): 5-10 phút
- File trung bình (50-200 trang): 15-30 phút
- File lớn (200-1000 trang): 30 phút - 2 giờ

⚠️ **Giới hạn:**

- Cần kết nối Internet ổn định
- Không tắt ứng dụng trong khi đang dịch
- PDF có ảnh/biểu đồ sẽ không được dịch (chỉ dịch văn bản)
- Một số font đặc biệt có thể không hiển thị chính xác trong file đầu ra

⚠️ **Khuyến nghị:**

- Với file lớn (>500 trang), nên chia nhỏ thành nhiều file
- Kiểm tra kết quả với file nhỏ trước khi xử lý file lớn
- Đảm bảo đủ dung lượng ổ cứng (file đầu ra thường lớn hơn file gốc)

## Cấu Trúc Dự Án

```
Translator/
│
├── main_app.py          # File chính, giao diện GUI
├── translator.py        # Module dịch thuật
├── pdf_handler.py       # Module xử lý PDF
├── requirements.txt     # Danh sách thư viện cần thiết
├── README.md           # File hướng dẫn này
│
├── install.bat         # Script cài đặt thư viện
├── run.bat             # Script chạy ứng dụng Python
├── build_exe.bat       # Script đóng gói thành EXE
│
└── dist/               # Thư mục chứa file EXE (sau khi build)
    └── PDF_Translator.exe
```

## Xử Lý Lỗi

### Lỗi khi chạy file .bat trong PowerShell

**Lỗi:** `The term 'install.bat' is not recognized...`

**Giải pháp:**

- Thêm `.\` trước tên file: `.\install.bat` hoặc `.\run.bat`
- Hoặc double-click trực tiếp vào file .bat

### Lỗi "Module not found"

```powershell
# Cài đặt lại các thư viện
pip install -r requirements.txt --force-reinstall
```

### Lỗi "Connection timeout"

- Kiểm tra kết nối Internet
- Thử lại sau vài phút
- Nếu vẫn lỗi, có thể Google Translate API tạm thời bị quá tải

### Lỗi "Memory Error" với file lớn

- Chia file PDF thành nhiều phần nhỏ hơn
- Đóng các ứng dụng khác để giải phóng RAM

## Công Nghệ Sử Dụng

- **PyMuPDF (fitz):** Xử lý đọc và tạo PDF
- **deep-translator:** API dịch thuật Google Translate
- **tkinter:** Giao diện đồ họa
- **Python threading:** Xử lý đa luồng

## Giấy Phép

Dự án này được phát triển cho mục đích học tập và sử dụng cá nhân.

## Liên Hệ & Hỗ Trợ

Nếu gặp vấn đề hoặc có câu hỏi, vui lòng tạo issue trên GitHub hoặc liên hệ trực tiếp.

---

**Lưu ý:** Ứng dụng sử dụng Google Translate API miễn phí, chất lượng dịch có thể không hoàn hảo 100%. Với tài liệu quan trọng, nên có người kiểm tra và hi교chỉnh sau khi dịch.
