import re
from typing import Any
from app.core.config import settings


class ChunkingService:
    """
    Service phân đoạn văn bản (Text Chunking):
    - Chia văn bản lớn thành các đoạn nhỏ (chunks) theo cửa sổ trượt (sliding window).
    - Giữ lại thông tin ngữ cảnh với độ chồng lấp (chunk_overlap).
    - Ưu tiên cắt theo ranh giới đoạn văn (\n\n), câu (. ! ?) để bảo toàn ngữ nghĩa.
    """

    @staticmethod
    def chunk_extracted_pages(
        pages: list[dict[str, Any]],
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ) -> list[dict[str, Any]]:
        """
        Nhận danh sách pages trích xuất từ ExtractorService:
        Trả về danh sách chunks:
        [
            {
                "chunk_index": 0,
                "content": "...",
                "token_count": 85,
                "metadata": {"page_number": 1}
            },
            ...
        ]
        """
        all_chunks: list[dict[str, Any]] = []
        global_chunk_idx = 0

        for page in pages:
            text = page.get("text", "").strip()
            page_num = page.get("page_number", 1)

            if not text:
                continue

            page_chunks = ChunkingService._split_text_with_overlap(
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            for c_text in page_chunks:
                # Ước lượng token (~4 ký tự = 1 token theo chuẩn OpenAI/Gemini)
                est_tokens = max(1, len(c_text) // 4)
                all_chunks.append({
                    "chunk_index": global_chunk_idx,
                    "content": c_text,
                    "token_count": est_tokens,
                    "metadata": {
                        "page_number": page_num
                    }
                })
                global_chunk_idx += 1

        return all_chunks

    @staticmethod
    def _split_text_with_overlap(
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> list[str]:
        """Tách một đoạn văn bản theo chunk_size và chunk_overlap."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size

            if end >= text_len:
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Cố gắng tìm vị trí cắt tự nhiên (dấu chấm câu hoặc xuống dòng) trong khoảng lân cận
            best_break = -1
            search_window = text[max(start, end - 100):end]
            
            # Ưu tiên ngắt ở \n hoặc dấu chấm câu
            breaks = [m.end() for m in re.finditer(r'(\n\n|\n|\.\s|\?\s|\!\s)', search_window)]
            if breaks:
                best_break = max(start, end - 100) + breaks[-1]

            if best_break != -1 and best_break > start:
                end = best_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Cửa sổ trượt
            start = end - chunk_overlap
            if start < 0 or start >= end:
                start = end

        return chunks
