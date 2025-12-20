"""
Module xử lý PDF - Dịch và giữ nguyên layout
Phương pháp: Tìm kiếm text gốc -> Xóa -> Chèn text dịch
Giống cách onlinedoctranslator.com hoạt động
"""

import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os
import re


@dataclass
class TextBlock:
    """Class đại diện cho một khối văn bản trong PDF"""
    text: str  # Text đã dịch (hoặc text gốc nếu chưa dịch)
    original_text: str = ""  # Text gốc tiếng Anh
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)  # (x0, y0, x1, y1)
    font_size: float = 11.0
    font_name: str = ""
    color: Tuple[float, float, float] = (0, 0, 0)  # RGB (0-1)
    page_num: int = 0
    flags: int = 0  # Font flags (bold, italic, etc.)


class PDFHandler:
    """
    Class xử lý PDF chuyên nghiệp - giống onlinedoctranslator.com
    
    Quy trình:
    1. Extract text với vị trí và format
    2. Dịch text (ở module khác)  
    3. Tìm và thay thế text trong PDF gốc
    """
    
    def __init__(self):
        """Khởi tạo PDF handler"""
        self.viet_font_path = self._find_vietnamese_font()
        self._font_cache = {}  # Cache font đã load
        
        if self.viet_font_path:
            print(f"✓ Font tiếng Việt: {self.viet_font_path}")
        else:
            print("⚠ Không tìm thấy font hỗ trợ tiếng Việt!")
    
    def _find_vietnamese_font(self) -> Optional[str]:
        """Tìm font hỗ trợ tiếng Việt Unicode"""
        import platform
        
        if platform.system() == "Windows":
            fonts_dir = "C:/Windows/Fonts"
            candidates = [
                f"{fonts_dir}/arial.ttf",
                f"{fonts_dir}/arialuni.ttf",
                f"{fonts_dir}/tahoma.ttf", 
                f"{fonts_dir}/segoeui.ttf",
                f"{fonts_dir}/calibri.ttf",
                f"{fonts_dir}/times.ttf",
                f"{fonts_dir}/verdana.ttf",
            ]
        elif platform.system() == "Darwin":
            candidates = [
                "/Library/Fonts/Arial.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        else:  # Linux
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
        
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def extract_text_with_format(self, pdf_path: str,
                                progress_callback: Optional[callable] = None) -> List[TextBlock]:
        """
        Trích xuất text từ PDF - GỘP CẢ LINE thay vì từng span
        Giống cách onlinedoctranslator.com xử lý
        """
        text_blocks = []
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            
            # Lấy text với đầy đủ thông tin
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:  # Chỉ xử lý text block
                    continue
                    
                # GỘP CẢ LINE thay vì lấy từng span
                for line in block.get("lines", []):
                    # Gộp tất cả spans trong một line
                    line_text = ""
                    line_bbox = None
                    max_font_size = 0
                    dominant_font = ""
                    dominant_color = (0, 0, 0)
                    flags = 0
                    
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        line_text += span_text
                        
                        # Tính bbox bao toàn bộ line
                        span_bbox = span.get("bbox", (0, 0, 0, 0))
                        if line_bbox is None:
                            line_bbox = list(span_bbox)
                        else:
                            line_bbox[0] = min(line_bbox[0], span_bbox[0])  # x0
                            line_bbox[1] = min(line_bbox[1], span_bbox[1])  # y0
                            line_bbox[2] = max(line_bbox[2], span_bbox[2])  # x1
                            line_bbox[3] = max(line_bbox[3], span_bbox[3])  # y1
                        
                        # Lấy font size lớn nhất
                        if span.get("size", 0) > max_font_size:
                            max_font_size = span.get("size", 11)
                            dominant_font = span.get("font", "")
                            dominant_color = self._int_to_rgb(span.get("color", 0))
                            flags = span.get("flags", 0)
                    
                    # Chỉ thêm nếu có nội dung
                    if line_text.strip():
                        text_blocks.append(TextBlock(
                            text=line_text,
                            original_text=line_text,
                            bbox=tuple(line_bbox) if line_bbox else (0, 0, 0, 0),
                            font_size=max_font_size,
                            font_name=dominant_font,
                            color=dominant_color,
                            page_num=page_num,
                            flags=flags
                        ))
            
            if progress_callback:
                progress_callback(page_num + 1, total_pages, "Đang đọc")
        
        doc.close()
        print(f"Đã trích xuất {len(text_blocks)} text lines (gộp từ spans)")
        return text_blocks

    def create_translated_pdf(self, original_pdf_path: str,
                            translated_blocks: List[TextBlock],
                            output_path: str,
                            progress_callback: Optional[callable] = None):
        """
        Tạo PDF với text đã dịch - giữ nguyên layout và format
        
        Phương pháp: Page-by-page replacement
        1. Với mỗi trang, tìm tất cả text instances
        2. Xóa text gốc bằng cách vẽ rect trắng đè lên
        3. Chèn text dịch vào đúng vị trí
        """
        doc = fitz.open(original_pdf_path)
        total_pages = len(doc)
        
        # Nhóm blocks theo trang
        blocks_by_page: Dict[int, List[TextBlock]] = {}
        for block in translated_blocks:
            page_num = block.page_num
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)
        
        # Xử lý từng trang
        for page_num in range(total_pages):
            page = doc[page_num]
            
            if page_num in blocks_by_page:
                self._process_page(page, blocks_by_page[page_num])
            
            if progress_callback:
                progress_callback(page_num + 1, total_pages, "Đang tạo PDF")
        
        # Lưu file
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        
        print(f"✓ Đã lưu PDF: {output_path}")

    def _process_page(self, page, blocks: List[TextBlock]):
        """
        Xử lý một trang PDF:
        1. Che text gốc bằng rectangle trắng
        2. Chèn text dịch vào đúng vị trí
        """
        # Sắp xếp blocks theo vị trí (top-to-bottom, left-to-right)
        blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
        
        # Bước 1: Che tất cả text gốc
        for block in blocks:
            try:
                rect = fitz.Rect(block.bbox)
                # Mở rộng rect một chút để che hết text
                rect = rect + (-1, -1, 1, 1)
                
                # Vẽ rectangle trắng đè lên text gốc
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            except Exception as e:
                pass
        
        # Bước 2: Chèn text dịch
        for block in blocks:
            self._insert_text(page, block)

    def _insert_text(self, page, block: TextBlock):
        """
        Chèn text vào trang PDF với font tiếng Việt
        Hỗ trợ text wrapping và tự động điều chỉnh kích thước
        """
        text = block.text
        if not text or not text.strip():
            return
        
        rect = fitz.Rect(block.bbox)
        font_size = block.font_size
        color = block.color
        
        # Điều chỉnh font size thông minh hơn
        if block.original_text:
            original_len = len(block.original_text)
            translated_len = len(text)
            
            # Nếu text dịch dài hơn 30%, giảm font
            if translated_len > original_len * 1.3 and original_len > 0:
                len_ratio = translated_len / original_len
                font_size = font_size / (len_ratio * 0.8)
                font_size = max(font_size, 6)  # Minimum 6pt
        
        # Mở rộng rect một chút để chứa text dịch
        rect_expanded = rect + (0, 0, rect.width * 0.05, rect.height * 0.1)
        
        try:
            if self.viet_font_path:
                # Thử các font size giảm dần
                font_sizes = [font_size, font_size * 0.9, font_size * 0.8, 
                             font_size * 0.7, font_size * 0.6, max(6, font_size * 0.5)]
                
                success = False
                for fs in font_sizes:
                    try:
                        rc = page.insert_textbox(
                            rect_expanded,
                            text,
                            fontsize=fs,
                            fontfile=self.viet_font_path,
                            fontname="VNFont",
                            color=color,
                            align=fitz.TEXT_ALIGN_LEFT,
                        )
                        
                        if rc >= 0:  # Thành công
                            success = True
                            break
                    except:
                        continue
                
                # Nếu insert_textbox thất bại, dùng insert_text
                if not success:
                    # Chia text thành nhiều dòng nếu quá dài
                    max_width = rect.width
                    avg_char_width = font_size * 0.5
                    max_chars = int(max_width / avg_char_width)
                    
                    if len(text) > max_chars:
                        # Word wrap
                        words = text.split()
                        lines = []
                        current_line = ""
                        
                        for word in words:
                            test_line = f"{current_line} {word}".strip()
                            if len(test_line) <= max_chars:
                                current_line = test_line
                            else:
                                if current_line:
                                    lines.append(current_line)
                                current_line = word
                        
                        if current_line:
                            lines.append(current_line)
                        
                        # Insert từng dòng
                        line_height = font_size * 1.15
                        y_pos = rect.y0 + font_size
                        
                        for line_text in lines:
                            if y_pos > rect.y1 + rect.height:
                                break
                            
                            point = fitz.Point(rect.x0, y_pos)
                            page.insert_text(
                                point,
                                line_text,
                                fontsize=font_size * 0.85,
                                fontfile=self.viet_font_path,
                                fontname="VNFont",
                                color=color,
                            )
                            y_pos += line_height
                    else:
                        # Text ngắn, insert một lần
                        point = fitz.Point(rect.x0, rect.y0 + font_size)
                        page.insert_text(
                            point,
                            text,
                            fontsize=font_size * 0.9,
                            fontfile=self.viet_font_path,
                            fontname="VNFont",
                            color=color,
                        )
                        
            else:
                # Fallback: không có font tiếng Việt (sẽ mất dấu)
                page.insert_textbox(
                    rect_expanded,
                    text, 
                    fontsize=font_size * 0.9,
                    fontname="helv",
                    color=color,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
                
        except Exception as e:
            # Silent fallback
            try:
                point = fitz.Point(rect.x0, rect.y0 + font_size * 0.8)
                page.insert_text(
                    point,
                    text,
                    fontsize=max(font_size * 0.6, 6),
                    fontname="helv",
                    color=color,
                )
            except:
                pass

    def _int_to_rgb(self, color_int: int) -> Tuple[float, float, float]:
        """Chuyển màu từ integer sang RGB float (0-1)"""
        r = ((color_int >> 16) & 0xFF) / 255.0
        g = ((color_int >> 8) & 0xFF) / 255.0
        b = (color_int & 0xFF) / 255.0
        return (r, g, b)

    def get_pdf_info(self, pdf_path: str) -> Dict:
        """Lấy thông tin PDF"""
        try:
            doc = fitz.open(pdf_path)
            info = {
                "page_count": len(doc),
                "metadata": doc.metadata,
                "file_size": os.path.getsize(pdf_path),
            }
            doc.close()
            return info
        except Exception as e:
            return {"error": str(e)}
