import os
from pathlib import Path
from typing import Any
import pypdf
import docx

from app.core.exceptions import InvalidFileException


class ExtractorService:
    """
    Service trích xuất nội dung văn bản từ các định dạng tệp:
    - PDF: Sử dụng pypdf đọc theo từng trang (kèm số trang).
    - DOCX: Sử dụng python-docx đọc các đoạn văn bản (paragraphs).
    - TXT: Đọc trực tiếp định dạng UTF-8 (có fallback các bảng mã thông dụng).
    """

    @staticmethod
    def extract_text(file_path: str) -> list[dict[str, Any]]:
        """
        Trích xuất văn bản từ tệp tin:
        Trả về danh sách các phần: [{"text": "...", "page_number": 1}, ...]
        """
        if not os.path.exists(file_path):
            raise InvalidFileException(f"Tệp tin không tồn tại: {file_path}")

        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return ExtractorService._extract_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return ExtractorService._extract_docx(file_path)
        elif ext == ".txt":
            return ExtractorService._extract_txt(file_path)
        else:
            raise InvalidFileException(f"Định dạng tệp '{ext}' chưa được hỗ trợ trích xuất.")

    @staticmethod
    def _extract_pdf(file_path: str) -> list[dict[str, Any]]:
        """Trích xuất từ file PDF theo từng trang."""
        results = []
        try:
            reader = pypdf.PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                clean_text = text.strip()
                if clean_text:
                    results.append({
                        "text": clean_text,
                        "page_number": page_idx + 1
                    })
        except Exception as e:
            raise InvalidFileException(f"Không thể đọc file PDF: {str(e)}")

        if not results:
            raise InvalidFileException("File PDF không chứa văn bản có thể trích xuất (có thể là file scan dạng ảnh)")

        return results

    @staticmethod
    def _extract_docx(file_path: str) -> list[dict[str, Any]]:
        """Trích xuất từ file DOCX."""
        results = []
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())

            content = "\n".join(full_text)
            if content.strip():
                results.append({
                    "text": content.strip(),
                    "page_number": 1
                })
        except Exception as e:
            raise InvalidFileException(f"Không thể đọc file DOCX: {str(e)}")

        if not results:
            raise InvalidFileException("File DOCX rỗng hoặc không có nội dung văn bản")

        return results

    @staticmethod
    def _extract_txt(file_path: str) -> list[dict[str, Any]]:
        """Trích xuất từ file TXT với các bảng mã UTF-8, latin-1, cp1258 (Tiếng Việt)."""
        encodings = ["utf-8", "utf-8-sig", "cp1258", "latin-1"]
        content = ""

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if not content.strip():
            raise InvalidFileException("File TXT rỗng hoặc không thể giải mã nội dung")

        return [{
            "text": content.strip(),
            "page_number": 1
        }]
