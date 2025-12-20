"""
Module dịch thuật sử dụng deep-translator
Hỗ trợ dịch từ English sang Vietnamese
TỐI ƯU: Batch processing, Multi-threading, Caching, Timeout handling
"""

from deep_translator import GoogleTranslator
import time
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import threading
import re


class TextTranslator:
    """Class xử lý dịch văn bản từ English sang Vietnamese - TỐI ƯU HIỆU SUẤT"""
    
    def __init__(self):
        """Khởi tạo translator với tối ưu theo CPU"""
        import os
        
        self.max_chunk_size = 4500  # Giới hạn ký tự mỗi lần dịch Google
        self.cache: Dict[str, str] = {}  # Cache để không dịch lại text giống nhau
        self.cache_lock = threading.Lock()
        self.request_delay = 0.08  # Giảm delay xuống 80ms để dịch nhanh hơn
        
        # Tối ưu workers dựa trên CPU cores - TĂNG WORKERS
        cpu_count = os.cpu_count() or 4
        self.max_workers = min(cpu_count * 2, 12)  # Tăng lên x2, tối đa 12 workers
        print(f"⚡ CPU: {cpu_count} cores -> Sử dụng {self.max_workers} workers (tối ưu tốc độ)")
        
        self.request_timeout = 30  # Timeout 30 giây cho mỗi request
    
    def _get_translator(self):
        """Tạo translator mới cho mỗi thread"""
        return GoogleTranslator(source='en', target='vi')
    
    def _normalize_text(self, text: str) -> str:
        """Chuẩn hóa text để cache hiệu quả hơn"""
        return text.strip().lower()
    
    def _safe_translate(self, translator, text: str, max_retries: int = 3) -> str:
        """Dịch với retry và xử lý lỗi"""
        if not text or not text.strip():
            return text
            
        for attempt in range(max_retries):
            try:
                result = translator.translate(text)
                if result:
                    return result
            except Exception as e:
                error_msg = str(e)
                # Chỉ in lỗi đầu tiên để tránh spam log
                if attempt == 0:
                    print(f"Lỗi dịch (sẽ retry): {error_msg[:100]}")
                if attempt < max_retries - 1:
                    # Tăng thời gian chờ dần lên cho các lần retry
                    wait_time = (attempt + 1) * 2  # 2s, 4s
                    time.sleep(wait_time)
        
        return text  # Trả về text gốc nếu thất bại
    
    def translate_text(self, text: str) -> str:
        """Dịch văn bản từ English sang Vietnamese"""
        if not text or not text.strip():
            return text
        
        # Kiểm tra cache
        cache_key = self._normalize_text(text)
        with self.cache_lock:
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        try:
            translator = self._get_translator()
            
            if len(text) <= self.max_chunk_size:
                result = self._safe_translate(translator, text)
            else:
                result = self._translate_long_text(text, translator)
            
            # Lưu vào cache
            with self.cache_lock:
                self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"Lỗi khi dịch: {e}")
            return text
    
    def _translate_long_text(self, text: str, translator) -> str:
        """Dịch văn bản dài bằng cách chia nhỏ"""
        sentences = self._split_into_sentences(text)
        translated_parts = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    translated_parts.append(self._safe_translate(translator, current_chunk))
                current_chunk = sentence
            else:
                current_chunk += sentence
        
        if current_chunk:
            translated_parts.append(self._safe_translate(translator, current_chunk))
        
        return " ".join(translated_parts)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Chia văn bản thành các câu"""
        sentences = re.split(r'([.!?\n]+\s*)', text)
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        return [s for s in result if s.strip()]
    
    def _create_batches(self, texts: List[str], batch_char_limit: int = 3000) -> List[List[tuple]]:
        """Gộp nhiều text ngắn vào 1 batch để giảm số lần gọi API"""
        batches = []
        current_batch = []
        current_length = 0
        
        for i, text in enumerate(texts):
            text_len = len(text) if text else 0
            
            if text_len > batch_char_limit:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_length = 0
                batches.append([(i, text)])
            elif current_length + text_len + 10 > batch_char_limit:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [(i, text)]
                current_length = text_len
            else:
                current_batch.append((i, text))
                current_length += text_len + 10
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _translate_batch_texts(self, batch: List[tuple], batch_id: int) -> List[tuple]:
        """Dịch một batch các text với xử lý lỗi tốt hơn"""
        results = []
        
        try:
            translator = self._get_translator()
            SEPARATOR = " ||| "
            
            # Kiểm tra cache trước
            texts_to_translate = []
            
            for idx, text in batch:
                if not text or not text.strip():
                    results.append((idx, text))
                else:
                    cache_key = self._normalize_text(text)
                    with self.cache_lock:
                        if cache_key in self.cache:
                            results.append((idx, self.cache[cache_key]))
                        else:
                            texts_to_translate.append((idx, text))
            
            if not texts_to_translate:
                return results
            
            # Dịch từng text một (an toàn hơn batch)
            for idx, text in texts_to_translate:
                try:
                    translated = self._safe_translate(translator, text)
                    results.append((idx, translated))
                    
                    # Cache kết quả
                    cache_key = self._normalize_text(text)
                    with self.cache_lock:
                        self.cache[cache_key] = translated
                    
                    time.sleep(self.request_delay)
                except Exception as e:
                    print(f"Lỗi dịch text {idx}: {e}")
                    results.append((idx, text))
            
        except Exception as e:
            print(f"Lỗi batch {batch_id}: {e}")
            # Trả về text gốc nếu lỗi
            for idx, text in batch:
                if idx not in [r[0] for r in results]:
                    results.append((idx, text))
        
        return results
    
    def translate_batch(self, texts: List[str], delay: float = 0.1, 
                       progress_callback: Optional[callable] = None) -> List[str]:
        """
        Dịch nhiều đoạn văn bản với TỐI ƯU HIỆU SUẤT
        """
        self.request_delay = delay
        total = len(texts)
        translated_texts = [""] * total
        completed_count = [0]  # Dùng list để có thể modify trong closure
        completed_lock = threading.Lock()
        
        # Tạo các batch
        batches = self._create_batches(texts)
        total_batches = len(batches)
        
        print(f"Tối ưu: {total} text -> {total_batches} batches")
        
        def process_batch(batch_data):
            batch_id, batch = batch_data
            try:
                results = self._translate_batch_texts(batch, batch_id)
                
                # Cập nhật kết quả
                for idx, translated in results:
                    translated_texts[idx] = translated
                
                # Cập nhật progress
                with completed_lock:
                    completed_count[0] += len(batch)
                    if progress_callback:
                        progress_callback(completed_count[0], total)
                
                return True
            except Exception as e:
                print(f"Lỗi xử lý batch {batch_id}: {e}")
                # Đánh dấu đã xử lý để không bị treo
                with completed_lock:
                    completed_count[0] += len(batch)
                    if progress_callback:
                        progress_callback(completed_count[0], total)
                return False
        
        # Chạy song song với timeout
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(process_batch, (i, batch)): (i, batch) 
                for i, batch in enumerate(batches)
            }
            
            # Đợi với timeout và xử lý lỗi
            try:
                for future in as_completed(future_to_batch, timeout=7200):  # Timeout 2 giờ
                    batch_id, batch = future_to_batch[future]
                    try:
                        future.result(timeout=600)  # Timeout 10 phút mỗi batch
                    except TimeoutError:
                        print(f"Batch {batch_id} timeout, giữ text gốc...")
                        # Giữ text gốc cho các item trong batch bị timeout
                        for idx, text in batch:
                            if not translated_texts[idx]:
                                translated_texts[idx] = text
                    except Exception as e:
                        print(f"Lỗi batch {batch_id}: {e}")
                        # Giữ text gốc nếu lỗi
                        for idx, text in batch:
                            if not translated_texts[idx]:
                                translated_texts[idx] = text
            except TimeoutError:
                print(f"\nCảnh báo: Đã timeout tổng thể, xử lý các batch còn lại...")
                # Xử lý các batch chưa hoàn thành
                for future, (batch_id, batch) in future_to_batch.items():
                    if not future.done():
                        print(f"Batch {batch_id} chưa xong, giữ text gốc")
                        for idx, text in batch:
                            if not translated_texts[idx]:
                                translated_texts[idx] = text
        
        # Đảm bảo không có text rỗng
        for i in range(total):
            if not translated_texts[i]:
                translated_texts[i] = texts[i]
        
        # Gọi callback lần cuối để đảm bảo 100%
        if progress_callback:
            progress_callback(total, total)
        
        print(f"Hoàn thành! Cache: {len(self.cache)} unique texts")
        
        return translated_texts
