import hashlib
import numpy as np
from app.core.config import settings

EMBEDDING_DIMENSION = 768


class EmbeddingService:
    """
    Service tạo vector nhúng (Embeddings):
    - Sử dụng mô hình Google Gemini text-embedding-004 (768 chiều).
    - Chuẩn hóa vector (L2 normalize) để tối ưu tính toán Cosine Similarity trong FAISS.
    - Có cơ chế tạo vector giả lập thông minh khi chưa cấu hình API key giúp test offline không lỗi.
    """

    @staticmethod
    def get_embedding(text: str) -> list[float]:
        """Tạo vector embedding cho 1 đoạn văn bản."""
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * EMBEDDING_DIMENSION

        is_real_key = (
            settings.GEMINI_API_KEY 
            and "your_gemini_api" not in settings.GEMINI_API_KEY.lower()
        )

        if is_real_key:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.embed_content(
                    model=settings.EMBEDDING_MODEL,
                    contents=clean_text,
                    config={"output_dimensionality": EMBEDDING_DIMENSION}
                )
                if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                    vec = np.array(response.embedding.values, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec.tolist()
                elif hasattr(response, "embeddings") and len(response.embeddings) > 0:
                    vec = np.array(response.embeddings[0].values, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec.tolist()
            except Exception as e:
                print(f"[EmbeddingService] Gemini embedding warning: {e}. Sử dụng fallback.")

        # Fallback tạo vector xác định (deterministic) dựa trên mã băm của từ vựng
        return EmbeddingService._generate_fallback_embedding(clean_text)

    @staticmethod
    def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
        """Tạo embeddings hàng loạt cho danh sách văn bản."""
        return [EmbeddingService.get_embedding(t) for t in texts]

    @staticmethod
    def _generate_fallback_embedding(text: str) -> list[float]:
        """
        Tạo vector 768 chiều giả lập có tính tương đồng ngữ nghĩa cơ bản qua n-gram/word hashing:
        Đảm bảo các văn bản có cùng từ khóa sẽ có cosine similarity cao trong FAISS.
        """
        vec = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        words = text.lower().split()
        for word in words:
            # Hash từng từ vào các chiều trong không gian 768
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % EMBEDDING_DIMENSION
            weight = 1.0 + ((h >> 8) % 100) / 100.0
            vec[idx] += weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            vec[0] = 1.0
        return vec.tolist()
