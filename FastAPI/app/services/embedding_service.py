from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


class GeminiEmbeddings(GoogleGenerativeAIEmbeddings):
    """
    Embedding Service chuẩn LangChain sử dụng Google Gemini Embeddings:
    - Kế thừa trực tiếp GoogleGenerativeAIEmbeddings của LangChain.
    - Tự động nạp model và API key từ cấu hình hệ thống.
    - Tương thích 100% với FAISS VectorStore.
    """

    def __init__(self, **kwargs):
        model_name = settings.EMBEDDING_MODEL
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        super().__init__(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            **kwargs
        )

    def embed_documents(
        self,
        texts: list[str],
        *,
        batch_size: int = 20,
        **kwargs
    ) -> list[list[float]]:
        """
        Embed danh sách các đoạn văn bản an toàn:
        - Chia thành các batch nhỏ (20 chunks/lần) để tránh vượt quá hạn mức API Free Tier (100 req/min).
        - Tự động bắt lỗi 429 RESOURCE_EXHAUSTED và sleep retry.
        - Tạm dừng ngắn giữa các batch lớn để bảo vệ quota.
        """
        import time
        import re

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            max_retries = 4
            for attempt in range(max_retries):
                try:
                    batch_embeddings = super().embed_documents(batch, batch_size=batch_size, **kwargs)
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    err_str = str(e)
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                        match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                        wait_seconds = float(match.group(1)) + 2.0 if match else (10.0 * (attempt + 1))
                        wait_seconds = min(wait_seconds, 60.0)
                        print(f"[GeminiEmbeddings] Quota limit (429) hit. Waiting {wait_seconds:.1f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_seconds)
                    else:
                        raise e

            # Nếu còn batch tiếp theo, tạm dừng ngắn để giãn request
            if i + batch_size < len(texts):
                time.sleep(1.0)

        return all_embeddings

    def embed_query(self, text: str, **kwargs) -> list[float]:
        import time
        import re

        max_retries = 3
        for attempt in range(max_retries):
            try:
                return super().embed_query(text, **kwargs)
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                    match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                    wait_seconds = float(match.group(1)) + 2.0 if match else (5.0 * (attempt + 1))
                    print(f"[GeminiEmbeddings] Rate limit on query. Waiting {wait_seconds:.1f}s...")
                    time.sleep(wait_seconds)
                else:
                    raise e


# Alias tương thích ngược
GeminiEmbeddings768 = GeminiEmbeddings
