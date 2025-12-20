"""
UI Tab Tách PDF - Giống splitapdf.com
- Preview thumbnails các trang
- Click để chọn/bỏ chọn  
- Scroll để xem nhiều trang
- Hỗ trợ tách theo range hoặc click chọn
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import threading
import os
from pathlib import Path
from PIL import Image, ImageTk
import io
import fitz  # PyMuPDF

from modules.pdf_splitter import PDFSplitter


class SplitPDFTab:
    """Tab tách PDF với preview thumbnail"""
    
    def __init__(self, parent, log_callback=None):
        self.parent = parent
        self.log = log_callback or print
        
        # PDF Splitter
        self.splitter = PDFSplitter()
        
        # State
        self.pdf_path = None
        self.thumbnail_images = {}  # Cache thumbnails
        self.page_frames = []  # Frame của mỗi trang
        self.is_processing = False
        self.output_files = []  # Files đã tách
        self.last_clicked_page = None  # Để hỗ trợ Shift+Click
        
        # Tạo UI
        self.create_ui()
    
    def create_ui(self):
        """Tạo giao diện tab tách PDF"""
        # === OUTER SCROLL: Bọc toàn bộ nội dung ===
        outer_canvas = tk.Canvas(self.parent, highlightthickness=0)
        outer_scrollbar = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=outer_canvas.yview)
        
        outer_canvas.configure(yscrollcommand=outer_scrollbar.set)
        outer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        outer_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Main frame bên trong canvas
        self.main_frame = ttk.Frame(outer_canvas)
        outer_canvas.create_window((0, 0), window=self.main_frame, anchor=tk.NW)
        
        # Bind scroll
        def on_main_configure(e):
            outer_canvas.configure(scrollregion=outer_canvas.bbox("all"))
            # Đặt width = canvas width
            outer_canvas.itemconfig(outer_canvas.find_all()[0], width=outer_canvas.winfo_width())
        
        self.main_frame.bind('<Configure>', on_main_configure)
        outer_canvas.bind('<Configure>', lambda e: outer_canvas.itemconfig(
            outer_canvas.find_all()[0], width=e.width))
        
        # Scroll bằng mouse wheel trên toàn bộ
        def on_outer_mousewheel(e):
            outer_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        
        outer_canvas.bind_all('<MouseWheel>', on_outer_mousewheel)
        
        # === TOP: Chọn file và thông tin ===
        top_frame = ttk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(10, 10), padx=10)
        
        # Chọn file
        ttk.Label(top_frame, text="File PDF:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar(value="Chưa chọn file")
        ttk.Entry(top_frame, textvariable=self.file_var, state='readonly', width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📂 Chọn File", command=self.select_file).pack(side=tk.LEFT)
        
        # Thông tin
        self.info_var = tk.StringVar(value="")
        ttk.Label(top_frame, textvariable=self.info_var, foreground="blue").pack(side=tk.LEFT, padx=20)
        
        # === TOOLBAR: Các nút thao tác ===
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Button(toolbar, text="✓ Chọn tất cả", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✗ Bỏ chọn tất cả", command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Chọn theo range
        ttk.Label(toolbar, text="Từ trang:").pack(side=tk.LEFT, padx=(0, 2))
        self.from_var = tk.StringVar(value="1")
        ttk.Entry(toolbar, textvariable=self.from_var, width=5).pack(side=tk.LEFT)
        
        ttk.Label(toolbar, text="đến:").pack(side=tk.LEFT, padx=(5, 2))
        self.to_var = tk.StringVar(value="1")
        ttk.Entry(toolbar, textvariable=self.to_var, width=5).pack(side=tk.LEFT)
        
        ttk.Button(toolbar, text="Chọn range", command=self.select_range).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Tách mỗi N trang
        ttk.Label(toolbar, text="Tách mỗi:").pack(side=tk.LEFT, padx=(0, 2))
        self.split_every_var = tk.StringVar(value="10")
        ttk.Entry(toolbar, textvariable=self.split_every_var, width=5).pack(side=tk.LEFT)
        ttk.Label(toolbar, text="trang").pack(side=tk.LEFT, padx=(2, 5))
        ttk.Button(toolbar, text="Tách theo số trang", command=self.split_every_n).pack(side=tk.LEFT)
        
        # === PANED WINDOW: Chia đôi màn hình - Thumbnails bên trái, Controls bên phải ===
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # === LEFT PANEL: Thumbnails Preview (70%) ===
        left_panel = ttk.Frame(self.paned)
        self.paned.add(left_panel, weight=7)
        
        # Label hướng dẫn
        preview_label = ttk.Label(left_panel, text="📄 Click chọn trang | Shift+Click chọn range:", font=('Arial', 9, 'bold'))
        preview_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Canvas với scrollbar cho thumbnails
        preview_container = ttk.Frame(left_panel)
        preview_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(preview_container, bg='#f5f5f5', highlightthickness=1, highlightbackground='#ddd')
        self.scrollbar_y = ttk.Scrollbar(preview_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_x = ttk.Scrollbar(preview_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame bên trong canvas
        self.pages_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.pages_frame, anchor=tk.NW)
        
        # Bind scroll events cho thumbnails canvas
        self.pages_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        # Không dùng bind_all vì đã có outer scroll
        
        # Thông tin đã chọn
        self.selected_var = tk.StringVar(value="Đã chọn: 0 trang")
        ttk.Label(left_panel, textvariable=self.selected_var, font=('Arial', 10, 'bold'), foreground='#2196F3').pack(anchor=tk.W, pady=(5, 0))
        
        # === RIGHT PANEL: Controls ===
        # === RIGHT PANEL: Controls (30%) ===
        right_panel = ttk.Frame(self.paned)
        self.paned.add(right_panel, weight=3)
        
        # -- Section 1: Tách nhanh --
        quick_frame = ttk.LabelFrame(right_panel, text="⚡ Tách nhanh")
        quick_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tách mỗi N trang
        row1 = ttk.Frame(quick_frame)
        row1.pack(fill=tk.X, padx=5, pady=3)
        ttk.Label(row1, text="Tách mỗi:").pack(side=tk.LEFT)
        self.split_every_var = tk.StringVar(value="10")
        ttk.Entry(row1, textvariable=self.split_every_var, width=5).pack(side=tk.LEFT, padx=3)
        ttk.Label(row1, text="trang").pack(side=tk.LEFT)
        ttk.Button(row1, text="Tách", command=self.split_every_n, width=8).pack(side=tk.RIGHT)
        
        # -- Section 2: Multi-range --
        multi_frame = ttk.LabelFrame(right_panel, text="📋 Tách theo ranges")
        multi_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Input ranges
        input_row = ttk.Frame(multi_frame)
        input_row.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_row, text="VD: 1-10, 20-30").pack(anchor=tk.W)
        self.multi_range_var = tk.StringVar(value="")
        self.multi_range_entry = ttk.Entry(input_row, textvariable=self.multi_range_var)
        self.multi_range_entry.pack(fill=tk.X, pady=2)
        
        # Buttons
        btn_row1 = ttk.Frame(multi_frame)
        btn_row1.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(btn_row1, text="📋 Preview", command=self.preview_multi_ranges).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="➕ Từ selection", command=self.add_selection_to_ranges).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row1, text="🗑️ Xóa", command=self.clear_preview_ranges).pack(side=tk.RIGHT, padx=2)
        
        # Preview table với scrollbar
        tree_container = ttk.Frame(multi_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('select', 'range', 'pages', 'filename')
        self.preview_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=6)
        
        self.preview_tree.heading('select', text='✓')
        self.preview_tree.heading('range', text='Range')
        self.preview_tree.heading('pages', text='Trang')
        self.preview_tree.heading('filename', text='Tên file')
        
        self.preview_tree.column('select', width=25, stretch=False)
        self.preview_tree.column('range', width=70, stretch=False)
        self.preview_tree.column('pages', width=60, stretch=False)
        self.preview_tree.column('filename', width=200, stretch=True)
        
        preview_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=preview_scroll.set)
        
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events cho preview tree
        self.preview_tree.bind('<Button-1>', self._on_preview_click)
        self.preview_tree.bind('<Double-1>', self._on_preview_double_click)
        
        # Row 3: Buttons ở dưới
        btn_row = ttk.Frame(multi_frame)
        btn_row.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_row, text="✓ Tất cả", command=self.select_all_preview, width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_row, text="✗ Bỏ chọn", command=self.deselect_all_preview, width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(btn_row, text="🗑️ Xóa", command=self.remove_selected_preview, width=6).pack(side=tk.LEFT, padx=1)
        
        # Download buttons
        download_row = ttk.Frame(multi_frame)
        download_row.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Button(download_row, text="📥 Tải đã chọn", command=self.download_selected_ranges).pack(side=tk.LEFT, padx=2)
        ttk.Button(download_row, text="📥 Tải tất cả", command=self.download_all_ranges).pack(side=tk.LEFT, padx=2)
        
        # Lưu trữ ranges preview
        self.preview_ranges = []  # List of {'range': (start, end), 'filename': str, 'selected': bool}
        
        # === BOTTOM: Nút tách ===
        bottom_frame = ttk.Frame(self.main_frame)
        bottom_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.split_btn = ttk.Button(bottom_frame, text="✂️ TÁCH PDF (theo selection)", command=self.start_split)
        self.split_btn.pack(side=tk.RIGHT, padx=5)
        
        # === OUTPUT FILES: Danh sách file đã tách ===
        output_frame = ttk.LabelFrame(self.main_frame, text="📥 Files đã tách (Click đúp để mở)")
        output_frame.pack(fill=tk.X, pady=(10, 10), padx=10)
        
        # Treeview cho danh sách files
        columns = ('filename', 'pages', 'size', 'path')
        self.output_tree = ttk.Treeview(output_frame, columns=columns, show='headings', height=4)
        
        self.output_tree.heading('filename', text='Tên file')
        self.output_tree.heading('pages', text='Số trang')
        self.output_tree.heading('size', text='Kích thước')
        self.output_tree.heading('path', text='Đường dẫn')
        
        self.output_tree.column('filename', width=200)
        self.output_tree.column('pages', width=80)
        self.output_tree.column('size', width=100)
        self.output_tree.column('path', width=300)
        
        # Scrollbar cho treeview
        tree_scroll = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_tree.yview)
        self.output_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.output_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double click để mở file
        self.output_tree.bind('<Double-1>', self.open_output_file)
        
        # Buttons cho output
        output_btn_frame = ttk.Frame(self.main_frame)
        output_btn_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        ttk.Button(output_btn_frame, text="📂 Mở thư mục", command=self.open_output_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(output_btn_frame, text="🗑️ Xóa danh sách", command=self.clear_output_list).pack(side=tk.LEFT, padx=2)
    
    def _on_frame_configure(self, event):
        """Cập nhật scroll region khi frame thay đổi"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Điều chỉnh chiều rộng frame khi canvas thay đổi"""
        pass  # Không cần điều chỉnh vì dùng grid
    
    def _on_mousewheel(self, event):
        """Scroll bằng mouse wheel"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def select_file(self):
        """Chọn file PDF"""
        filename = filedialog.askopenfilename(
            title="Chọn file PDF cần tách",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if filename:
            self.pdf_path = filename
            self.file_var.set(filename)
            self.log(f"Đã chọn: {Path(filename).name}")
            
            # Load PDF
            if self.splitter.load_pdf(filename):
                self.info_var.set(f"📄 {self.splitter.total_pages} trang")
                self.to_var.set(str(self.splitter.total_pages))
                self.load_thumbnails()
            else:
                messagebox.showerror("Lỗi", "Không thể đọc file PDF!")
    
    def load_thumbnails(self):
        """Load thumbnails cho tất cả trang"""
        # Xóa thumbnails cũ
        for widget in self.pages_frame.winfo_children():
            widget.destroy()
        
        self.thumbnail_images.clear()
        self.page_frames.clear()
        
        if not self.splitter.doc:
            return
        
        # Hiển thị loading
        loading_label = ttk.Label(self.pages_frame, text="⏳ Đang tải preview...")
        loading_label.pack()
        self.parent.update()
        
        # Load trong thread
        threading.Thread(target=self._load_thumbnails_thread, daemon=True).start()
    
    def _load_thumbnails_thread(self):
        """Load thumbnails trong background thread"""
        try:
            total = self.splitter.total_pages
            
            # Xóa loading label
            self.parent.after(0, lambda: self._clear_pages_frame())
            
            # Tính số cột dựa trên chiều rộng canvas
            cols = 6  # Mặc định 6 cột
            thumb_size = 120
            
            for i in range(total):
                # Lấy thumbnail
                png_data = self.splitter.get_page_thumbnail(i, thumb_size)
                
                if png_data:
                    # Tạo UI trong main thread
                    self.parent.after(0, lambda idx=i, data=png_data: self._add_thumbnail(idx, data, cols))
                
                # Cập nhật progress
                if (i + 1) % 10 == 0:
                    self.parent.after(0, lambda p=i+1, t=total: self.log(f"Đang tải: {p}/{t} trang"))
            
            self.parent.after(0, lambda: self.log(f"✓ Đã tải xong {total} trang"))
            self.parent.after(0, self._update_selected_count)
            
        except Exception as e:
            self.parent.after(0, lambda: self.log(f"Lỗi load thumbnails: {e}"))
    
    def _clear_pages_frame(self):
        """Xóa tất cả widget trong pages_frame"""
        for widget in self.pages_frame.winfo_children():
            widget.destroy()
    
    def _add_thumbnail(self, page_idx: int, png_data: bytes, cols: int):
        """Thêm một thumbnail vào grid"""
        try:
            # Tạo image từ PNG data
            img = Image.open(io.BytesIO(png_data))
            photo = ImageTk.PhotoImage(img)
            
            # Lưu reference
            self.thumbnail_images[page_idx] = photo
            
            # Tạo frame cho trang này
            frame = ttk.Frame(self.pages_frame, padding=5)
            row = page_idx // cols
            col = page_idx % cols
            frame.grid(row=row, column=col, padx=5, pady=5)
            
            # Label hiển thị ảnh
            img_label = tk.Label(frame, image=photo, cursor='hand2', 
                                borderwidth=3, relief='groove', bg='white')
            img_label.pack()
            
            # Label số trang
            page_label = ttk.Label(frame, text=f"Trang {page_idx + 1}")
            page_label.pack()
            
            # Checkbox để hiển thị trạng thái chọn
            is_selected = page_idx in self.splitter.selected_pages
            
            # Bind click event - hỗ trợ Shift+Click và Ctrl+Click
            img_label.bind('<Button-1>', lambda e, idx=page_idx: self._on_page_click(e, idx))
            img_label.bind('<Shift-Button-1>', lambda e, idx=page_idx: self._on_shift_click(e, idx))
            img_label.bind('<Control-Button-1>', lambda e, idx=page_idx: self._on_ctrl_click(e, idx))
            
            page_label.bind('<Button-1>', lambda e, idx=page_idx: self._on_page_click(e, idx))
            page_label.bind('<Shift-Button-1>', lambda e, idx=page_idx: self._on_shift_click(e, idx))
            page_label.bind('<Control-Button-1>', lambda e, idx=page_idx: self._on_ctrl_click(e, idx))
            
            # Lưu reference đến frame và label
            self.page_frames.append({
                'frame': frame,
                'img_label': img_label,
                'page_label': page_label,
                'index': page_idx
            })
            
            # Cập nhật màu border nếu đã chọn
            if is_selected:
                img_label.configure(borderwidth=4, relief='solid', bg='#4CAF50')
            
        except Exception as e:
            print(f"Lỗi thêm thumbnail {page_idx}: {e}")
    
    def _on_page_click(self, event, page_idx: int):
        """Xử lý click thường - chọn/bỏ chọn một trang"""
        self.toggle_page(page_idx)
        self.last_clicked_page = page_idx
    
    def _on_shift_click(self, event, page_idx: int):
        """Xử lý Shift+Click - chọn range từ trang cuối click đến trang hiện tại"""
        if self.last_clicked_page is None:
            # Chưa có trang nào được click trước đó
            self.toggle_page(page_idx)
            self.last_clicked_page = page_idx
            return
        
        # Chọn range từ last_clicked đến page_idx
        start = min(self.last_clicked_page, page_idx)
        end = max(self.last_clicked_page, page_idx)
        
        # Chọn tất cả trang trong range
        for i in range(start, end + 1):
            if i not in self.splitter.selected_pages:
                self.splitter.selected_pages.add(i)
                if i < len(self.splitter.pages):
                    self.splitter.pages[i].selected = True
        
        # Cập nhật UI
        self._update_all_page_visuals()
        self._update_selected_count()
        
        self.log(f"Đã chọn trang {start + 1} - {end + 1}")
    
    def _on_ctrl_click(self, event, page_idx: int):
        """Xử lý Ctrl+Click - toggle chọn trang mà không reset selection"""
        self.toggle_page(page_idx)
        self.last_clicked_page = page_idx
    
    def _update_all_page_visuals(self):
        """Cập nhật visual cho tất cả các trang"""
        for pf in self.page_frames:
            idx = pf['index']
            if idx in self.splitter.selected_pages:
                pf['img_label'].configure(borderwidth=4, relief='solid', bg='#4CAF50')
            else:
                pf['img_label'].configure(borderwidth=3, relief='groove', bg='white')

    def toggle_page(self, page_idx: int):
        """Chọn/bỏ chọn một trang"""
        is_selected = self.splitter.toggle_page(page_idx)
        
        # Cập nhật UI
        for pf in self.page_frames:
            if pf['index'] == page_idx:
                if is_selected:
                    pf['img_label'].configure(borderwidth=4, relief='solid', bg='#4CAF50')
                else:
                    pf['img_label'].configure(borderwidth=3, relief='groove', bg='white')
                break
        
        self._update_selected_count()
    
    def select_all(self):
        """Chọn tất cả trang"""
        self.splitter.select_all()
        
        for pf in self.page_frames:
            pf['img_label'].configure(borderwidth=4, relief='solid', bg='#4CAF50')
        
        self._update_selected_count()
    
    def deselect_all(self):
        """Bỏ chọn tất cả"""
        self.splitter.deselect_all()
        
        for pf in self.page_frames:
            pf['img_label'].configure(borderwidth=3, relief='groove', bg='white')
        
        self._update_selected_count()
    
    def select_range(self):
        """Chọn một range trang"""
        try:
            start = int(self.from_var.get())
            end = int(self.to_var.get())
            
            if start < 1 or end > self.splitter.total_pages or start > end:
                messagebox.showwarning("Cảnh báo", f"Range không hợp lệ! (1-{self.splitter.total_pages})")
                return
            
            self.splitter.select_range(start, end)
            
            # Cập nhật UI
            for pf in self.page_frames:
                idx = pf['index']
                if idx in self.splitter.selected_pages:
                    pf['img_label'].configure(borderwidth=4, relief='solid', bg='#4CAF50')
            
            self._update_selected_count()
            self.log(f"Đã chọn trang {start} - {end}")
            
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập số trang hợp lệ!")
    
    def _update_selected_count(self):
        """Cập nhật số trang đã chọn"""
        count = self.splitter.get_selected_count()
        self.selected_var.set(f"Đã chọn: {count} trang")
    
    def start_split(self):
        """Bắt đầu tách PDF"""
        if not self.splitter.doc:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file PDF trước!")
            return
        
        if self.splitter.get_selected_count() == 0:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất 1 trang!")
            return
        
        # Chọn nơi lưu
        suggested_name = self.splitter.get_suggested_filename()
        
        output_path = filedialog.asksaveasfilename(
            title="Lưu file PDF đã tách",
            defaultextension=".pdf",
            initialfile=suggested_name,
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not output_path:
            return
        
        # Tách trong thread
        self.is_processing = True
        self.split_btn.configure(state='disabled')
        
        threading.Thread(target=self._split_thread, args=(output_path,), daemon=True).start()
    
    def _split_thread(self, output_path: str):
        """Thread tách PDF"""
        try:
            self.parent.after(0, lambda: self.log("Đang tách PDF..."))
            
            success = self.splitter.split_selected(output_path, 
                lambda cur, total: self.parent.after(0, lambda: self.log(f"Đang xử lý: {cur}/{total}")))
            
            if success:
                self.parent.after(0, lambda: self._on_split_complete(output_path))
            else:
                self.parent.after(0, lambda: messagebox.showerror("Lỗi", "Không thể tách PDF!"))
                
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self.is_processing = False
            self.parent.after(0, lambda: self.split_btn.configure(state='normal'))
    
    def _on_split_complete(self, output_path: str):
        """Khi tách xong"""
        # Thêm vào danh sách output
        self._add_output_file(output_path)
        
        self.log(f"✓ Đã tách xong: {Path(output_path).name}")
        messagebox.showinfo("Thành công", f"Đã tách {self.splitter.get_selected_count()} trang!\n\nFile: {output_path}")
    
    def split_every_n(self):
        """Tách mỗi N trang"""
        if not self.splitter.doc:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file PDF trước!")
            return
        
        try:
            n = int(self.split_every_var.get())
            if n <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập số trang hợp lệ!")
            return
        
        # Chọn thư mục lưu
        output_dir = filedialog.askdirectory(title="Chọn thư mục lưu các file")
        
        if not output_dir:
            return
        
        # Tách trong thread
        self.is_processing = True
        self.split_btn.configure(state='disabled')
        
        threading.Thread(target=self._split_every_n_thread, args=(n, output_dir), daemon=True).start()
    
    def _split_every_n_thread(self, n: int, output_dir: str):
        """Thread tách mỗi N trang"""
        try:
            self.parent.after(0, lambda: self.log(f"Đang tách mỗi {n} trang..."))
            
            files = self.splitter.split_every_n_pages(n, output_dir, 
                progress_callback=lambda cur, total, name: self.parent.after(0, lambda: self.log(f"Đã tạo: {name}")))
            
            if files:
                for f in files:
                    self.parent.after(0, lambda fp=f: self._add_output_file(fp))
                
                self.parent.after(0, lambda: messagebox.showinfo("Thành công", f"Đã tách thành {len(files)} file!"))
            else:
                self.parent.after(0, lambda: messagebox.showerror("Lỗi", "Không thể tách PDF!"))
                
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self.is_processing = False
            self.parent.after(0, lambda: self.split_btn.configure(state='normal'))
    
    def _add_output_file(self, filepath: str):
        """Thêm file vào danh sách output"""
        try:
            # Lấy thông tin file
            filename = Path(filepath).name
            size = os.path.getsize(filepath)
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            
            # Đếm số trang
            try:
                doc = fitz.open(filepath)
                pages = len(doc)
                doc.close()
            except:
                pages = "?"
            
            # Thêm vào treeview
            self.output_tree.insert('', 'end', values=(filename, f"{pages} trang", size_str, filepath))
            
            self.output_files.append(filepath)
            
        except Exception as e:
            print(f"Lỗi thêm file vào danh sách: {e}")
    
    def open_output_file(self, event):
        """Mở file khi double click"""
        selection = self.output_tree.selection()
        if selection:
            item = self.output_tree.item(selection[0])
            filepath = item['values'][3]
            
            if os.path.exists(filepath):
                os.startfile(filepath)
    
    def open_output_folder(self):
        """Mở thư mục chứa file output"""
        if self.output_files:
            folder = os.path.dirname(self.output_files[-1])
            os.startfile(folder)
        else:
            messagebox.showinfo("Thông báo", "Chưa có file nào được tách!")
    
    def clear_output_list(self):
        """Xóa danh sách file output"""
        for item in self.output_tree.get_children():
            self.output_tree.delete(item)
        self.output_files.clear()
    
    def clear_preview_ranges(self):
        """Xóa preview ranges"""
        self.preview_ranges.clear()
        self.multi_range_var.set("")
        self._refresh_preview_tree()
    
    # ============ MULTI-RANGE METHODS ============
    
    def preview_multi_ranges(self):
        """Preview các file sẽ tạo từ input ranges - CLEAR và tạo mới"""
        if not self.splitter.doc:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file PDF trước!")
            return
        
        ranges_text = self.multi_range_var.get().strip()
        if not ranges_text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập ranges!\nVD: 1-10, 20-30, 50-100")
            return
        
        # Parse ranges
        ranges = self._parse_ranges(ranges_text)
        if not ranges:
            messagebox.showerror("Lỗi", "Không thể parse ranges!\nVD: 1-10, 20-30, 50-100")
            return
        
        # CLEAR trước khi thêm mới
        self.preview_ranges.clear()
        
        # Validate và thêm vào preview
        base_name = Path(self.pdf_path).stem
        added = 0
        
        for start, end in ranges:
            # Validate
            if start < 1 or end > self.splitter.total_pages or start > end:
                self.log(f"⚠ Bỏ qua range không hợp lệ: {start}-{end}")
                continue
            
            # Check trùng range
            is_duplicate = any(item['range'] == (start, end) for item in self.preview_ranges)
            if is_duplicate:
                self.log(f"⚠ Bỏ qua range trùng: {start}-{end}")
                continue
            
            # Tạo tên file
            filename = f"{base_name}_pages_{start}-{end}.pdf"
            
            # Thêm vào preview list
            self.preview_ranges.append({
                'range': (start, end),
                'filename': filename,
                'selected': True
            })
            added += 1
        
        self._refresh_preview_tree()
        self.log(f"✓ Preview {added} files từ ranges")
    
    def add_selection_to_ranges(self):
        """Thêm các trang đã chọn vào ranges"""
        if not self.splitter.doc:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file PDF trước!")
            return
        
        if self.splitter.get_selected_count() == 0:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất 1 trang!")
            return
        
        # Lấy các trang đã chọn và gộp thành ranges liên tiếp
        selected = sorted(self.splitter.selected_pages)
        ranges = []
        
        start = selected[0] + 1  # Convert to 1-indexed
        end = start
        
        for i in range(1, len(selected)):
            page = selected[i] + 1  # 1-indexed
            if page == end + 1:
                end = page
            else:
                ranges.append((start, end))
                start = page
                end = page
        
        ranges.append((start, end))
        
        # Thêm vào input
        current = self.multi_range_var.get().strip()
        new_ranges = ", ".join([f"{s}-{e}" for s, e in ranges])
        
        if current:
            self.multi_range_var.set(f"{current}, {new_ranges}")
        else:
            self.multi_range_var.set(new_ranges)
        
        # Auto preview
        self.preview_multi_ranges()
    
    def _parse_ranges(self, text: str) -> list:
        """Parse text thành list of (start, end) tuples"""
        ranges = []
        
        # Hỗ trợ cả dấu phẩy, dấu chấm phẩy và newline
        text = text.replace(';', ',').replace('\n', ',')
        parts = [p.strip() for p in text.split(',') if p.strip()]
        
        for part in parts:
            if '-' in part:
                try:
                    start, end = part.split('-')
                    ranges.append((int(start.strip()), int(end.strip())))
                except:
                    pass
        
        return ranges
    
    def _refresh_preview_tree(self):
        """Refresh preview treeview"""
        # Clear
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # Add items
        for i, item in enumerate(self.preview_ranges):
            start, end = item['range']
            pages = end - start + 1
            check = "✓" if item['selected'] else ""
            
            self.preview_tree.insert('', 'end', iid=str(i),
                values=(check, f"{start}-{end}", f"{pages} trang", item['filename']))
    
    def _on_preview_click(self, event):
        """Click vào preview tree - toggle select"""
        region = self.preview_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.preview_tree.identify_column(event.x)
            item = self.preview_tree.identify_row(event.y)
            
            if item and column == "#1":  # Click vào cột select
                idx = int(item)
                if 0 <= idx < len(self.preview_ranges):
                    self.preview_ranges[idx]['selected'] = not self.preview_ranges[idx]['selected']
                    self._refresh_preview_tree()
    
    def _on_preview_double_click(self, event):
        """Double click để sửa tên file"""
        item = self.preview_tree.selection()
        if not item:
            return
        
        idx = int(item[0])
        if 0 <= idx < len(self.preview_ranges):
            current_name = self.preview_ranges[idx]['filename']
            
            # Hiện dialog nhập tên mới
            new_name = simpledialog.askstring(
                "Đổi tên file",
                "Nhập tên file mới:",
                initialvalue=current_name
            )
            
            if new_name and new_name.strip():
                if not new_name.endswith('.pdf'):
                    new_name += '.pdf'
                self.preview_ranges[idx]['filename'] = new_name
                self._refresh_preview_tree()
    
    def select_all_preview(self):
        """Chọn tất cả trong preview"""
        for item in self.preview_ranges:
            item['selected'] = True
        self._refresh_preview_tree()
    
    def deselect_all_preview(self):
        """Bỏ chọn tất cả trong preview"""
        for item in self.preview_ranges:
            item['selected'] = False
        self._refresh_preview_tree()
    
    def remove_selected_preview(self):
        """Xóa các item đã chọn trong preview"""
        self.preview_ranges = [item for item in self.preview_ranges if not item['selected']]
        self._refresh_preview_tree()
    
    def download_selected_ranges(self):
        """Tải các file đã chọn trong preview"""
        selected_items = [item for item in self.preview_ranges if item['selected']]
        
        if not selected_items:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất 1 file!")
            return
        
        self._download_ranges(selected_items)
    
    def download_all_ranges(self):
        """Tải tất cả files trong preview"""
        if not self.preview_ranges:
            messagebox.showwarning("Cảnh báo", "Chưa có file nào trong preview!")
            return
        
        self._download_ranges(self.preview_ranges)
    
    def _download_ranges(self, items: list):
        """Tải các ranges đã chọn"""
        if not self.splitter.doc:
            return
        
        # Chọn thư mục lưu
        output_dir = filedialog.askdirectory(title="Chọn thư mục lưu các file")
        
        if not output_dir:
            return
        
        # Tách trong thread
        self.is_processing = True
        self.split_btn.configure(state='disabled')
        
        threading.Thread(target=self._download_ranges_thread, args=(items, output_dir), daemon=True).start()
    
    def _download_ranges_thread(self, items: list, output_dir: str):
        """Thread tải các ranges"""
        try:
            total = len(items)
            success = 0
            
            self.parent.after(0, lambda: self.log(f"Đang tách {total} files..."))
            
            for i, item in enumerate(items):
                try:
                    start, end = item['range']
                    filename = item['filename']
                    output_path = os.path.join(output_dir, filename)
                    
                    self.parent.after(0, lambda n=filename: self.log(f"  Đang tạo: {n}"))
                    
                    # Tách PDF
                    new_doc = fitz.open()
                    new_doc.insert_pdf(self.splitter.doc, from_page=start-1, to_page=end-1)
                    new_doc.save(output_path)
                    new_doc.close()
                    
                    # Thêm vào output list
                    self.parent.after(0, lambda fp=output_path: self._add_output_file(fp))
                    
                    success += 1
                    
                except Exception as e:
                    self.parent.after(0, lambda err=str(e): self.log(f"  ❌ Lỗi: {err}"))
            
            self.parent.after(0, lambda: self.log(f"✓ Hoàn thành: {success}/{total} files"))
            self.parent.after(0, lambda: messagebox.showinfo("Thành công", 
                f"Đã tách {success}/{total} files!\n\nThư mục: {output_dir}"))
            
            # Hỏi mở thư mục
            if success > 0:
                self.parent.after(100, lambda: self._ask_open_folder(output_dir))
                
        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
        finally:
            self.is_processing = False
            self.parent.after(0, lambda: self.split_btn.configure(state='normal'))
    
    def _ask_open_folder(self, folder: str):
        """Hỏi mở thư mục sau khi tách"""
        if messagebox.askyesno("Hoàn thành", "Mở thư mục chứa files?"):
            os.startfile(folder)
