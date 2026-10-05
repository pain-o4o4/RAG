import time
import hashlib
import numpy as np
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


class GeminiEmbeddings768(GoogleGenerativeAIEmbeddings):
    """
    Service tạo Vector Embeddings sử dụng Google Gemini API:
    - Kế thừa LangChain GoogleGenerativeAIEmbeddings để tương thích hoàn toàn với FAISS.
    - Ép kích thước về settings.EMBEDDING_DIMENSION (768 chiều) qua Matryoshka Representation Learning.
    - Chuẩn hóa L2 vector (||v|| = 1) để tính toán Cosine Similarity trong FAISS (IndexFlatIP).
    - Hỗ trợ gửi theo batch 25 đoạn/lần kèm cơ chế tự động thử lại (Retry Backoff) khi gặp lỗi Rate Limit (429).
    - Có cơ chế Fallback tạo vector giả lập deterministic khi chưa có API Key hoặc lỗi mạng giúp test không bị crash.
    """

    def _fallback_768(self, text: str) -> list[float]:
        clean = text.strip() or "fallback"
        h = hashlib.sha256(clean.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "little")
        rng = np.random.RandomState(seed)
        vec = rng.randn(settings.EMBEDDING_DIMENSION).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Tạo vector nhúng cho 1 câu hỏi tìm kiếm."""
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * settings.EMBEDDING_DIMENSION

        try:
            from google import genai
            client = genai.Client(api_key=self.google_api_key.get_secret_value())
            for attempt in range(4):
                try:
                    resp = client.models.embed_content(
                        model=self.model,
                        contents=clean_text,
                        config={"output_dimensionality": settings.EMBEDDING_DIMENSION}
                    )
                    vec = np.array(resp.embeddings[0].values, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec.tolist()
                except Exception as e:
                    err_msg = str(e).lower()
                    if ("429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg) and attempt < 3:
                        wait_sec = 5 * (attempt + 1)
                        print(f"[GeminiEmbeddings768] Rate limit on query, retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                    else:
                        raise e
        except Exception as e:
            print(f"[GeminiEmbeddings768] Error embedding query: {e}. Fallback to deterministic 768.")
            return self._fallback_768(clean_text)

        return self._fallback_768(clean_text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Tạo vector nhúng cho danh sách các đoạn văn bản (có chia batching & retry)."""
        if not texts:
            return []

        try:
            from google import genai
            client = genai.Client(api_key=self.google_api_key.get_secret_value())
        except Exception as e:
            print(f"[GeminiEmbeddings768] Error initializing genai client: {e}")
            return [self._fallback_768(t) for t in texts]

        all_vectors = []
        batch_size = 25

        for i in range(0, len(texts), batch_size):
            batch = [t.strip() or " " for t in texts[i:i + batch_size]]
            batch_success = False

            for attempt in range(5):
                try:
                    from google.genai import types
                    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in batch]
                    resp = client.models.embed_content(
                        model=self.model,
                        contents=contents,
                        config={"output_dimensionality": settings.EMBEDDING_DIMENSION}
                    )
                    if resp.embeddings and len(resp.embeddings) == len(batch):
                        for emb in resp.embeddings:
                            vec = np.array(emb.values, dtype=np.float32)
                            norm = np.linalg.norm(vec)
                            if norm > 0:
                                vec = vec / norm
                            all_vectors.append(vec.tolist())
                        batch_success = True
                        time.sleep(0.2)
                        break
                    else:
                        raise ValueError(f"Expected {len(batch)} embeddings, got {len(resp.embeddings) if resp.embeddings else 0}")
                except Exception as e:
                    err_msg = str(e).lower()
                    if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                        wait_sec = 8 * (attempt + 1)
                        print(f"[GeminiEmbeddings768] Rate limit in batch {i}..{i+len(batch)}, waiting {wait_sec}s (attempt {attempt+1}/5)...")
                        time.sleep(wait_sec)
                    else:
                        print(f"[GeminiEmbeddings768] Batch error: {e}")
                        break

            if not batch_success:
                print(f"[GeminiEmbeddings768] Fallback for batch {i}..{i+len(batch)}")
                for t in batch:
                    try:
                        resp = client.models.embed_content(
                            model=self.model,
                            contents=t,
                            config={"output_dimensionality": settings.EMBEDDING_DIMENSION}
                        )
                        vec = np.array(resp.embeddings[0].values, dtype=np.float32)
                        norm = np.linalg.norm(vec)
                        if norm > 0:
                            vec = vec / norm
                        all_vectors.append(vec.tolist())
                    except Exception:
                        all_vectors.append(self._fallback_768(t))

        return all_vectors
