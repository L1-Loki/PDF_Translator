"""
Ứng dụng dịch PDF từ English sang Vietnamese
Giao diện đồ họa sử dụng tkinter với System Tray support
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import time
import sys
from pathlib import Path

# Import pystray cho system tray
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠ pystray không có - không hỗ trợ system tray")

from translator import TextTranslator
from pdf_handler import PDFHandler


class PDFTranslatorApp:
    """Ứng dụng dịch PDF với giao diện đồ họa"""
    
    def __init__(self, root):
        """Khởi tạo ứng dụng"""
        self.root = root
        self.root.title("Dịch PDF English - Vietnamese")
        self.root.geometry("800x600")
        
        # Khởi tạo các module
        self.translator = TextTranslator()
        self.pdf_handler = PDFHandler()
        
        # Biến lưu trữ
        self.input_pdf_path = None
        self.output_pdf_path = None
        self.is_processing = False
        self.translation_thread = None
        
        # System Tray
        self.tray_icon = None
        self.is_minimized_to_tray = False
        
        # Set icon cho app
        self.setup_icon()
        
        # Bắt sự kiện đóng cửa sổ -> minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Tạo giao diện
        self.create_widgets()
        
        # Setup system tray nếu có
        if TRAY_AVAILABLE:
            self.setup_tray()
    
    def setup_icon(self):
        """Load icon cho ứng dụng từ file Loki.png"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'Image', 'Loki.png')
            if os.path.exists(icon_path):
                # Load icon và set cho window
                icon_image = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_image)
                # Giữ reference để không bị garbage collected
                self.root._icon_image = icon_image
            else:
                print(f"⚠ Không tìm thấy icon tại: {icon_path}")
        except Exception as e:
            print(f"Lỗi load icon: {e}")
    
    def create_widgets(self):
        """Tạo các widget cho giao diện"""
        
        # Frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Cấu hình grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Tiêu đề
        title_label = ttk.Label(
            main_frame, 
            text="DỊCH PDF ENGLISH - VIETNAMESE",
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # Chọn file PDF đầu vào
        ttk.Label(main_frame, text="File PDF gốc:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.input_path_var = tk.StringVar()
        ttk.Entry(
            main_frame, 
            textvariable=self.input_path_var,
            state='readonly',
            width=50
        ).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(
            main_frame,
            text="Chọn File",
            command=self.select_input_file
        ).grid(row=1, column=2, pady=5)
        
        # Chọn file PDF đầu ra
        ttk.Label(main_frame, text="Lưu kết quả:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.output_path_var = tk.StringVar()
        ttk.Entry(
            main_frame,
            textvariable=self.output_path_var,
            state='readonly',
            width=50
        ).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(
            main_frame,
            text="Chọn Vị Trí",
            command=self.select_output_file
        ).grid(row=2, column=2, pady=5)
        
        # Frame thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin PDF", padding="10")
        info_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        info_frame.columnconfigure(1, weight=1)
        
        ttk.Label(info_frame, text="Số trang:").grid(row=0, column=0, sticky=tk.W)
        self.page_count_var = tk.StringVar(value="---")
        ttk.Label(info_frame, textvariable=self.page_count_var).grid(
            row=0, column=1, sticky=tk.W, padx=10
        )
        
        ttk.Label(info_frame, text="Kích thước:").grid(row=1, column=0, sticky=tk.W)
        self.file_size_var = tk.StringVar(value="---")
        ttk.Label(info_frame, textvariable=self.file_size_var).grid(
            row=1, column=1, sticky=tk.W, padx=10
        )
        
        # Nút bắt đầu dịch
        self.translate_button = ttk.Button(
            main_frame,
            text="BẮT ĐẦU DỊCH",
            command=self.start_translation,
            style='Accent.TButton'
        )
        self.translate_button.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=600
        )
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Status label
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=('Arial', 10)
        )
        self.status_label.grid(row=6, column=0, columnspan=3, pady=5)
        
        # Log text area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=10, width=70)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Cấu hình grid weights
        main_frame.rowconfigure(7, weight=1)
    
    def select_input_file(self):
        """Chọn file PDF đầu vào"""
        filename = filedialog.askopenfilename(
            title="Chọn file PDF cần dịch",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if filename:
            self.input_pdf_path = filename
            self.input_path_var.set(filename)
            
            # Tự động đề xuất tên file output
            if not self.output_pdf_path:
                output_name = Path(filename).stem + "_translated.pdf"
                output_path = str(Path(filename).parent / output_name)
                self.output_pdf_path = output_path
                self.output_path_var.set(output_path)
            
            # Hiển thị thông tin PDF
            self.show_pdf_info(filename)
            self.log(f"Đã chọn file: {Path(filename).name}")
    
    def select_output_file(self):
        """Chọn vị trí lưu file PDF đầu ra"""
        filename = filedialog.asksaveasfilename(
            title="Chọn vị trí lưu file",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if filename:
            self.output_pdf_path = filename
            self.output_path_var.set(filename)
            self.log(f"File sẽ được lưu tại: {Path(filename).name}")
    
    def show_pdf_info(self, pdf_path):
        """Hiển thị thông tin về file PDF"""
        try:
            info = self.pdf_handler.get_pdf_info(pdf_path)
            self.page_count_var.set(str(info.get('page_count', '---')))
            
            file_size = info.get('file_size', 0)
            size_mb = file_size / (1024 * 1024)
            self.file_size_var.set(f"{size_mb:.2f} MB")
            
        except Exception as e:
            self.log(f"Lỗi khi đọc thông tin PDF: {e}")
    
    def start_translation(self):
        """Bắt đầu quá trình dịch"""
        if self.is_processing:
            messagebox.showwarning("Cảnh báo", "Đang xử lý, vui lòng đợi!")
            return
        
        if not self.input_pdf_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn file PDF cần dịch!")
            return
        
        if not self.output_pdf_path:
            messagebox.showerror("Lỗi", "Vui lòng chọn vị trí lưu file!")
            return
        
        # Xác nhận
        result = messagebox.askyesno(
            "Xác nhận",
            f"Bắt đầu dịch file có {self.page_count_var.get()} trang?\n"
            f"Quá trình có thể mất nhiều thời gian."
        )
        
        if not result:
            return
        
        # Chạy trong thread riêng
        self.is_processing = True
        self.translate_button.config(state='disabled')
        self.log("=" * 50)
        self.log("BẮT ĐẦU QUÁ TRÌNH DỊCH")
        self.log("=" * 50)
        self.log("⚠️ LƯU Ý: ĐỪNG ĐÓNG CỬA SỔ khi đang dịch!")
        self.log("Nếu minimize (thu nhỏ), quá trình vẫn tiếp tục chạy ngầm.")
        
        self.translation_thread = threading.Thread(target=self.translate_pdf)
        self.translation_thread.daemon = False  # Không dùng daemon để thread chạy hết
        self.translation_thread.start()
    
    def translate_pdf(self):
        """Thực hiện dịch PDF (chạy trong thread riêng)"""
        try:
            # Bước 1: Đọc PDF
            self.update_status("Đang đọc file PDF...")
            self.log("Bước 1: Đọc file PDF và trích xuất văn bản...")
            
            text_blocks = self.pdf_handler.extract_text_with_format(
                self.input_pdf_path,
                progress_callback=self.update_read_progress
            )
            
            total_blocks = len(text_blocks)
            self.log(f"Đã trích xuất {total_blocks} khối văn bản")
            
            # Bước 2: Dịch văn bản
            self.update_status("Đang dịch văn bản...")
            self.log("Bước 2: Dịch văn bản (có thể mất 30-60 phút với file lớn)...")
            self.log("Đang xử lý... vui lòng đợi...")
            
            start_time = time.time()
            
            translated_texts = self.translator.translate_batch(
                [block.text for block in text_blocks],
                delay=0.1,  # Tăng delay lên 100ms để ổn định hơn
                progress_callback=self.update_translate_progress
            )
            
            elapsed_time = time.time() - start_time
            self.log(f"Thời gian dịch: {elapsed_time/60:.1f} phút")
            
            # Cập nhật text blocks với văn bản đã dịch (giữ nguyên original_text)
            for i, block in enumerate(text_blocks):
                # original_text đã được lưu trong extract_text_with_format
                block.text = translated_texts[i]
            
            self.log(f"Đã dịch xong {len(translated_texts)} khối văn bản")
            
            # Bước 3: Tạo PDF mới
            self.update_status("Đang tạo file PDF mới...")
            self.log("Bước 3: Tạo file PDF với văn bản đã dịch...")
            
            self.pdf_handler.create_translated_pdf(
                self.input_pdf_path,
                text_blocks,
                self.output_pdf_path,
                progress_callback=self.update_create_progress
            )
            
            # Hoàn thành
            self.progress_var.set(100)
            self.update_status("Hoàn thành!")
            self.log("=" * 50)
            self.log(f"✅ HOÀN THÀNH! File đã được lưu tại:")
            self.log(self.output_pdf_path)
            self.log("=" * 50)
            
            # Restore cửa sổ nếu đang minimize
            if self.root.state() == 'iconic':
                self.root.deiconify()
            
            # Đưa cửa sổ lên trên
            self.root.lift()
            self.root.focus_force()
            
            self.root.after(0, lambda: messagebox.showinfo(
                "✅ Thành công",
                f"Dịch hoàn tất!\n\n"
                f"Thời gian: {elapsed_time/60:.1f} phút\n"
                f"File đã được lưu tại:\n{self.output_pdf_path}"
            ))
            
        except Exception as e:
            import traceback
            error_msg = f"Lỗi: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            error_str = str(e)  # Lưu error thành biến local
            self.root.after(0, lambda err=error_str: messagebox.showerror("Lỗi", err))
            
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.translate_button.config(state='normal'))
    
    def update_read_progress(self, current, total, phase):
        """Cập nhật tiến trình đọc PDF"""
        progress = (current / total) * 33.33  # 33% cho việc đọc
        self.progress_var.set(progress)
        self.update_status(f"{phase} PDF: {current}/{total} trang")
    
    def update_translate_progress(self, current, total):
        """Cập nhật tiến trình dịch"""
        progress = 33.33 + (current / total) * 33.33  # 33-66% cho việc dịch
        self.progress_var.set(progress)
        self.update_status(f"Đang dịch: {current}/{total} khối văn bản")
    
    def update_create_progress(self, current, total, phase):
        """Cập nhật tiến trình tạo PDF"""
        progress = 66.66 + (current / total) * 33.34  # 66-100% cho việc tạo PDF
        self.progress_var.set(progress)
        self.update_status(f"{phase}: {current}/{total} trang")
    
    def update_status(self, message):
        """Cập nhật status label"""
        self.status_var.set(message)
    
    def log(self, message):
        """Thêm message vào log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def on_closing(self):
        """Xử lý khi người dùng đóng cửa sổ - DEPRECATED, dùng minimize_to_tray"""
        self.minimize_to_tray()
    
    def minimize_to_tray(self):
        """Thu nhỏ vào system tray thay vì thoát"""
        if not TRAY_AVAILABLE:
            # Không có system tray, hỏi có muốn thoát không
            if self.is_processing:
                result = messagebox.askyesno(
                    "Xác nhận thoát",
                    "⚠️ ĐANG XỬ LÝ DỊCH!\n\n"
                    "Nếu đóng cửa sổ bây giờ, toàn bộ tiến trình sẽ BỊ HỦY!\n\n"
                    "Bạn có chắc muốn THOÁT không?"
                )
                if result:
                    self.quit_app()
            else:
                self.root.destroy()
            return
        
        # Có system tray - minimize vào đó
        if self.is_processing:
            self.log("📌 Thu nhỏ vào system tray - quá trình dịch tiếp tục chạy ngầm...")
        
        self.root.withdraw()  # Ẩn cửa sổ
        self.is_minimized_to_tray = True
        
        # Đảm bảo tray icon đang chạy
        if self.tray_icon and not self.tray_icon.visible:
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_window(self):
        """Hiện lại cửa sổ từ system tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.is_minimized_to_tray = False
    
    def quit_app(self):
        """Thoát ứng dụng hoàn toàn"""
        if self.is_processing:
            result = messagebox.askyesno(
                "Xác nhận thoát",
                "⚠️ ĐANG XỬ LÝ DỊCH!\n\n"
                "Toàn bộ tiến trình sẽ BỊ HỦY nếu thoát!\n\n"
                "Bạn có chắc chắn muốn THOÁT?"
            )
            if not result:
                return
            
            self.log("❌ Người dùng hủy quá trình dịch!")
            self.is_processing = False
        
        # Dừng tray icon nếu có
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def setup_tray(self):
        """Tạo system tray icon"""
        try:
            # Tạo icon đơn giản
            image = self.create_tray_icon()
            
            # Menu cho tray icon
            menu = pystray.Menu(
                item('Hiện cửa sổ', self.show_window, default=True),
                item('Thoát', self.quit_app)
            )
            
            # Tạo tray icon
            self.tray_icon = pystray.Icon(
                "pdf_translator",
                image,
                "Dịch PDF - Click để hiện",
                menu
            )
            
            # Chạy tray icon trong thread riêng
            # threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            print(f"Lỗi tạo system tray: {e}")
    
    def create_tray_icon(self):
        """Tạo icon cho system tray từ Loki.png"""
        try:
            # Thử load icon Loki
            icon_path = os.path.join(os.path.dirname(__file__), 'Image', 'Loki.png')
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                # Resize về 64x64 cho tray icon
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                return image
        except Exception as e:
            print(f"Lỗi load icon Loki: {e}")
        
        # Fallback: Tạo icon đơn giản
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), 'white')
        dc = ImageDraw.Draw(image)
        
        # Vẽ hình đại diện (chữ PDF màu xanh)
        dc.rectangle([0, 0, width, height], fill='#2196F3')
        dc.text((width//2 - 15, height//2 - 20), 'PDF', fill='white')
        
        return image


def main():
    """Hàm main để chạy ứng dụng"""
    root = tk.Tk()
    app = PDFTranslatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
