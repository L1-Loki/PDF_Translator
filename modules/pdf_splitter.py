"""
Module tách PDF với preview trang
Click để chọn/bỏ chọn trang, kéo để chọn nhiều trang
"""

import fitz  # PyMuPDF
from typing import List, Set, Optional, Callable
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class PageInfo:
    """Thông tin một trang PDF"""
    page_num: int  # 0-indexed
    width: float
    height: float
    selected: bool = False


class PDFSplitter:
    """Class xử lý tách PDF với preview"""
    
    def __init__(self):
        self.doc: Optional[fitz.Document] = None
        self.pdf_path: str = ""
        self.total_pages: int = 0
        self.pages: List[PageInfo] = []
        self.selected_pages: Set[int] = set()
        
    def load_pdf(self, pdf_path: str) -> bool:
        """Load file PDF"""
        try:
            if self.doc:
                self.doc.close()
            
            self.doc = fitz.open(pdf_path)
            self.pdf_path = pdf_path
            self.total_pages = len(self.doc)
            self.pages = []
            self.selected_pages = set()
            
            # Lấy thông tin các trang
            for i in range(self.total_pages):
                page = self.doc[i]
                rect = page.rect
                self.pages.append(PageInfo(
                    page_num=i,
                    width=rect.width,
                    height=rect.height,
                    selected=False
                ))
            
            return True
        except Exception as e:
            print(f"Lỗi load PDF: {e}")
            return False
    
    def get_page_thumbnail(self, page_num: int, max_size: int = 150) -> bytes:
        """Tạo thumbnail cho một trang (trả về PNG bytes)"""
        if not self.doc or page_num >= self.total_pages:
            return b''
        
        try:
            page = self.doc[page_num]
            
            # Tính zoom để fit vào max_size
            rect = page.rect
            zoom = min(max_size / rect.width, max_size / rect.height)
            
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            return pix.tobytes("png")
        except Exception as e:
            print(f"Lỗi tạo thumbnail trang {page_num}: {e}")
            return b''
    
    def toggle_page(self, page_num: int) -> bool:
        """Chọn/bỏ chọn một trang, trả về trạng thái mới"""
        if page_num in self.selected_pages:
            self.selected_pages.discard(page_num)
            if page_num < len(self.pages):
                self.pages[page_num].selected = False
            return False
        else:
            self.selected_pages.add(page_num)
            if page_num < len(self.pages):
                self.pages[page_num].selected = True
            return True
    
    def select_range(self, start: int, end: int):
        """Chọn một range trang (1-indexed input)"""
        start_idx = max(0, start - 1)
        end_idx = min(self.total_pages, end)
        
        for i in range(start_idx, end_idx):
            self.selected_pages.add(i)
            if i < len(self.pages):
                self.pages[i].selected = True
    
    def select_all(self):
        """Chọn tất cả trang"""
        self.selected_pages = set(range(self.total_pages))
        for page in self.pages:
            page.selected = True
    
    def deselect_all(self):
        """Bỏ chọn tất cả"""
        self.selected_pages.clear()
        for page in self.pages:
            page.selected = False
    
    def get_selected_count(self) -> int:
        """Số trang đã chọn"""
        return len(self.selected_pages)
    
    def split_selected(self, output_path: str, 
                      progress_callback: Optional[Callable] = None) -> bool:
        """Tách các trang đã chọn ra file mới"""
        if not self.doc or not self.selected_pages:
            return False
        
        try:
            # Sắp xếp các trang theo thứ tự
            pages_to_extract = sorted(self.selected_pages)
            
            # Tạo PDF mới
            new_doc = fitz.open()
            
            total = len(pages_to_extract)
            for i, page_num in enumerate(pages_to_extract):
                new_doc.insert_pdf(self.doc, from_page=page_num, to_page=page_num)
                
                if progress_callback:
                    progress_callback(i + 1, total)
            
            # Lưu file
            new_doc.save(output_path)
            new_doc.close()
            
            return True
        except Exception as e:
            print(f"Lỗi tách PDF: {e}")
            return False
    
    def split_by_ranges(self, ranges: List[tuple], output_dir: str,
                       base_name: str = "",
                       progress_callback: Optional[Callable] = None) -> List[str]:
        """
        Tách PDF theo nhiều ranges
        ranges: List của (start, end) - 1-indexed
        Trả về list các file đã tạo
        """
        if not self.doc:
            return []
        
        if not base_name:
            base_name = Path(self.pdf_path).stem
        
        created_files = []
        total_ranges = len(ranges)
        
        for idx, (start, end) in enumerate(ranges):
            try:
                # Chuyển sang 0-indexed
                start_idx = max(0, start - 1)
                end_idx = min(self.total_pages, end)
                
                if start_idx >= end_idx:
                    continue
                
                # Tạo tên file
                output_name = f"{base_name}_pages_{start}-{end}.pdf"
                output_path = os.path.join(output_dir, output_name)
                
                # Tạo PDF mới
                new_doc = fitz.open()
                new_doc.insert_pdf(self.doc, from_page=start_idx, to_page=end_idx - 1)
                new_doc.save(output_path)
                new_doc.close()
                
                created_files.append(output_path)
                
                if progress_callback:
                    progress_callback(idx + 1, total_ranges, output_name)
                    
            except Exception as e:
                print(f"Lỗi tách range {start}-{end}: {e}")
        
        return created_files
    
    def split_every_n_pages(self, n: int, output_dir: str,
                           base_name: str = "",
                           progress_callback: Optional[Callable] = None) -> List[str]:
        """Tách mỗi n trang thành 1 file"""
        if not self.doc or n <= 0:
            return []
        
        ranges = []
        for start in range(1, self.total_pages + 1, n):
            end = min(start + n - 1, self.total_pages)
            ranges.append((start, end))
        
        return self.split_by_ranges(ranges, output_dir, base_name, progress_callback)
    
    def get_suggested_filename(self) -> str:
        """Gợi ý tên file output"""
        if not self.pdf_path:
            return "output.pdf"
        
        base = Path(self.pdf_path).stem
        
        if self.selected_pages:
            pages = sorted(self.selected_pages)
            if len(pages) == 1:
                return f"{base}_page_{pages[0] + 1}.pdf"
            else:
                return f"{base}_pages_{pages[0] + 1}-{pages[-1] + 1}.pdf"
        
        return f"{base}_split.pdf"
    
    def close(self):
        """Đóng file PDF"""
        if self.doc:
            self.doc.close()
            self.doc = None
