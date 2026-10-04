import os
import uuid
import json
from typing import Optional, Any
import numpy as np

from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document as LangchainDocument
from app.core.config import settings

EMBEDDING_DIMENSION = 768


class GeminiEmbeddings768(GoogleGenerativeAIEmbeddings):
    """
    Embeddings wrapper tùy chỉnh dùng Google Gemini API:
    - Ép dimensionality về 768 chiều (Matryoshka Representation Learning) để tương thích và tối ưu tốc độ.
    - Chuẩn hóa L2 vector để tính toán Cosine Similarity qua Inner Product (IndexFlatIP).
    - Hỗ trợ batching tối đa 50 văn bản/lần gọi để không bị dính rate limit 429.
    """

    def embed_query(self, text: str) -> list[float]:
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * EMBEDDING_DIMENSION

        try:
            from google import genai
            client = genai.Client(api_key=self.google_api_key.get_secret_value())
            resp = client.models.embed_content(
                model=self.model,
                contents=clean_text,
                config={"output_dimensionality": EMBEDDING_DIMENSION}
            )
            vec = np.array(resp.embeddings[0].values, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.tolist()
        except Exception as e:
            print(f"[GeminiEmbeddings768] Error embedding query: {e}. Fallback to super.")
            try:
                return super().embed_query(clean_text)
            except Exception:
                return [0.0] * EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            from google import genai
            client = genai.Client(api_key=self.google_api_key.get_secret_value())
            all_vectors = []
            batch_size = 50

            for i in range(0, len(texts), batch_size):
                batch = [t.strip() or " " for t in texts[i:i + batch_size]]
                resp = client.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config={"output_dimensionality": EMBEDDING_DIMENSION}
                )
                for emb in resp.embeddings:
                    vec = np.array(emb.values, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    all_vectors.append(vec.tolist())

            return all_vectors
        except Exception as e:
            print(f"[GeminiEmbeddings768] Batch error: {e}. Fallback one-by-one.")
            return [self.embed_query(t) for t in texts]


class VectorStore:
    """
    Quản lý Vector Database sử dụng LangChain FAISS:
    - Quản lý tách biệt chỉ mục vector theo từng User ({user_id}.faiss và {user_id}.pkl).
    - Tự động di chuyển dữ liệu từ index cũ (.index, _meta.json) nếu cần.
    - Tìm kiếm ngữ nghĩa với hỗ trợ lọc document_id / document_ids và ngưỡng similarity_threshold.
    """

    def __init__(self, vector_dir: str = settings.VECTOR_STORE_DIR):
        self.vector_dir = vector_dir
        os.makedirs(self.vector_dir, exist_ok=True)
        try:
            self.embeddings = GeminiEmbeddings768(
                model=settings.EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY
            )
        except Exception:
            from langchain_community.embeddings import FakeEmbeddings
            self.embeddings = FakeEmbeddings(size=EMBEDDING_DIMENSION)

    def _get_index_name(self, user_id: uuid.UUID) -> str:
        return str(user_id)

    def _get_faiss_path(self, index_name: str) -> str:
        return os.path.join(self.vector_dir, f"{index_name}.faiss")

    def _migrate_old_index_if_needed(self, index_name: str) -> Optional[FAISS]:
        """Tự động chuyển đổi dữ liệu từ định dạng FAISS cũ (.index + _meta.json) sang LangChain FAISS."""
        old_index_file = os.path.join(self.vector_dir, f"{index_name}.index")
        old_meta_file = os.path.join(self.vector_dir, f"{index_name}_meta.json")

        if not (os.path.exists(old_index_file) and os.path.exists(old_meta_file)):
            return None

        try:
            import faiss
            from langchain_community.docstore.in_memory import InMemoryDocstore

            print(f"[VectorStore] Auto-migrating old index for user: {index_name}...")
            index = faiss.read_index(old_index_file)
            with open(old_meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            docstore = InMemoryDocstore({})
            index_to_docstore_id = {}

            for i, m in enumerate(meta):
                doc_id = str(i)
                d = LangchainDocument(
                    page_content=m.get("content", ""),
                    metadata={
                        "document_id": str(m.get("document_id", "")),
                        "chunk_index": m.get("chunk_index", i),
                        "page_number": m.get("metadata", {}).get("page_number", 1)
                    }
                )
                docstore.add({doc_id: d})
                index_to_docstore_id[i] = doc_id

            vectorstore = FAISS(
                embedding_function=self.embeddings,
                index=index,
                docstore=docstore,
                index_to_docstore_id=index_to_docstore_id
            )
            vectorstore.save_local(self.vector_dir, index_name=index_name)
            print(f"[VectorStore] Successfully migrated {len(meta)} chunks to LangChain FAISS!")
            return vectorstore
        except Exception as e:
            print(f"[VectorStore] Migration failed: {e}")
            return None

    def add_documents(
        self,
        user_id: uuid.UUID,
        documents: list[LangchainDocument]
    ) -> list[str]:
        index_name = self._get_index_name(user_id)
        faiss_path = self._get_faiss_path(index_name)

        if not os.path.exists(faiss_path):
            # Thử migrate nếu có file cũ
            self._migrate_old_index_if_needed(index_name)

        if os.path.exists(faiss_path):
            try:
                vectorstore = FAISS.load_local(
                    folder_path=self.vector_dir,
                    embeddings=self.embeddings,
                    index_name=index_name,
                    allow_dangerous_deserialization=True
                )
                vector_ids = vectorstore.add_documents(documents)
                vectorstore.save_local(self.vector_dir, index_name=index_name)
                return vector_ids
            except Exception as e:
                print(f"[VectorStore] Error adding to existing FAISS: {e}")

        # Tạo mới nếu chưa có
        vectorstore = FAISS.from_documents(documents, self.embeddings)
        vectorstore.save_local(self.vector_dir, index_name=index_name)
        return [str(uuid.uuid4()) for _ in documents]

    def search(
        self,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 4,
        document_id: Optional[uuid.UUID] = None,
        document_ids: Optional[list[uuid.UUID]] = None,
        similarity_threshold: float = settings.SIMILARITY_THRESHOLD
    ) -> list[dict[str, Any]]:
        index_name = self._get_index_name(user_id)
        faiss_path = self._get_faiss_path(index_name)

        vectorstore = None
        if os.path.exists(faiss_path):
            try:
                vectorstore = FAISS.load_local(
                    folder_path=self.vector_dir,
                    embeddings=self.embeddings,
                    index_name=index_name,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"[VectorStore] Error loading FAISS: {e}")

        if not vectorstore:
            vectorstore = self._migrate_old_index_if_needed(index_name)

        if not vectorstore:
            return []

        target_doc_ids = set()
        if document_ids:
            target_doc_ids = {str(d) for d in document_ids}
        elif document_id:
            target_doc_ids = {str(document_id)}

        def filter_func(meta: dict) -> bool:
            if not target_doc_ids:
                return True
            doc_id_in_meta = str(meta.get("document_id", ""))
            return doc_id_in_meta in target_doc_ids

        # Tìm kiếm k lớn hơn để sau đó lọc threshold và doc_ids
        search_k = min(vectorstore.index.ntotal, max(top_k * 4, 10))
        results = vectorstore.similarity_search_with_score(
            query,
            k=search_k,
            filter=filter_func if target_doc_ids else None
        )

        matched_results = []
        for doc, score in results:
            float_score = float(score)
            # Với IndexFlatIP (Cosine Similarity sau L2 normalize), giá trị score càng cao càng tương đồng
            if similarity_threshold > 0 and float_score < similarity_threshold:
                continue

            matched_results.append({
                "document_id": doc.metadata.get("document_id"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float_score
            })

            if len(matched_results) >= top_k:
                break

        return matched_results
