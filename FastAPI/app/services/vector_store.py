import os
import re
import uuid
from typing import Optional, Any

from rank_bm25 import BM25Plus
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LangchainDocument
from app.core.config import settings
from app.services.embedding_service import GeminiEmbeddings


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
            self.embeddings = GeminiEmbeddings()
        except Exception as e:
            print(f"[VectorStore] FATAL ERROR initializing GeminiEmbeddings: {e}")
            raise

    def _get_index_name(self, user_id: uuid.UUID) -> str:
        return str(user_id)

    def _get_faiss_path(self, index_name: str) -> str:
        return os.path.join(self.vector_dir, f"{index_name}.faiss")



    def add_documents(
        self,
        user_id: uuid.UUID,
        documents: list[LangchainDocument]
    ) -> list[str]:
        index_name = self._get_index_name(user_id)
        faiss_path = self._get_faiss_path(index_name)



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

    def delete_document_vectors(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID
    ) -> int:
        """
        Xóa toàn bộ các vector của document_id khỏi chỉ mục FAISS của user:
        - Quét danh sách tài liệu trong docstore của FAISS.
        - Tìm tất cả ID có metadata['document_id'] trùng với document_id cần xóa.
        - Gọi vectorstore.delete(ids_to_del) để loại bỏ các vector tương ứng.
        - Lưu lại chỉ mục FAISS đã cập nhật trên ổ đĩa.
        - Trả về số lượng vector đã xóa.
        """
        index_name = self._get_index_name(user_id)
        faiss_path = self._get_faiss_path(index_name)

        if not os.path.exists(faiss_path):
            return 0

        try:
            vectorstore = FAISS.load_local(
                folder_path=self.vector_dir,
                embeddings=self.embeddings,
                index_name=index_name,
                allow_dangerous_deserialization=True
            )
            target_str = str(document_id)
            ids_to_del = [
                docstore_id for docstore_id, doc in vectorstore.docstore._dict.items()
                if str(doc.metadata.get("document_id", "")) == target_str
            ]

            if not ids_to_del:
                return 0

            vectorstore.delete(ids_to_del)
            vectorstore.save_local(self.vector_dir, index_name=index_name)
            print(f"[VectorStore] Đã xóa {len(ids_to_del)} vectors của tài liệu {document_id} khỏi FAISS của user {user_id}")
            return len(ids_to_del)
        except Exception as e:
            print(f"[VectorStore] Lỗi khi xóa vector khỏi FAISS: {e}")
            return 0

    @staticmethod
    def _tokenize_vietnamese(text: str) -> list[str]:
        """Tách từ đơn giản và chuẩn hóa chữ thường cho BM25."""
        return [w.lower() for w in re.findall(r"\w+", text)]

    def search(
        self,
        user_id: uuid.UUID,
        query: str,
        top_k: int = settings.TOP_K_RESULTS,
        document_ids: Optional[list[uuid.UUID]] = None,
        similarity_threshold: float = settings.SIMILARITY_THRESHOLD,
        enable_hybrid: bool = True
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
            return []

        target_doc_ids = {str(d) for d in document_ids} if document_ids else set()

        def filter_func(meta: dict) -> bool:
            if not target_doc_ids:
                return True
            doc_id_in_meta = str(meta.get("document_id", ""))
            return doc_id_in_meta in target_doc_ids

        # Tự động phát hiện và khắc phục lệch chiều vector (Dimension Mismatch)
        try:
            test_query_vector = self.embeddings.embed_query(query)
            if vectorstore.index.d != len(test_query_vector):
                print(f"[VectorStore] Dimension mismatch detected ({vectorstore.index.d} != {len(test_query_vector)}). Rebuilding index for user {user_id}...")
                docs_to_reindex = list(vectorstore.docstore._dict.values())
                if docs_to_reindex:
                    vectorstore = FAISS.from_documents(docs_to_reindex, self.embeddings)
                    vectorstore.save_local(self.vector_dir, index_name=index_name)
                else:
                    return []
        except Exception as e:
            print(f"[VectorStore] Warning during query embedding check: {e}")

        # 1. Thu thập danh sách documents ứng viên (đã lọc theo target_doc_ids nếu có)
        all_docs_in_store = list(vectorstore.docstore._dict.values())
        candidate_docs = [d for d in all_docs_in_store if filter_func(d.metadata)]
        if not candidate_docs:
            return []

        # 2. VECTOR SEARCH (FAISS L2 -> Similarity)
        search_k = min(vectorstore.index.ntotal, max(top_k * 4, 15))
        try:
            raw_vector_results = vectorstore.similarity_search_with_score(
                query,
                k=search_k,
                filter=filter_func if target_doc_ids else None
            )
        except Exception as e:
            print(f"[VectorStore] FAISS search error: {e}")
            raw_vector_results = []

        vector_ranked_docs: list[tuple[LangchainDocument, float]] = []
        for doc, score in raw_vector_results:
            sim = 1.0 / (1.0 + max(0.0, float(score)))
            vector_ranked_docs.append((doc, sim))

        # 3. BM25 SPARSE SEARCH (BM25Plus - Khớp chính xác từ khóa / mã sản phẩm / số liệu)
        bm25_ranked_docs: list[tuple[LangchainDocument, float]] = []
        if enable_hybrid and candidate_docs:
            try:
                tokenized_corpus = [self._tokenize_vietnamese(d.page_content) for d in candidate_docs]
                bm25_model = BM25Plus(tokenized_corpus)
                query_tokens = self._tokenize_vietnamese(query)
                bm25_raw_scores = bm25_model.get_scores(query_tokens)

                bm25_candidates = [
                    (candidate_docs[i], float(bm25_raw_scores[i]))
                    for i in range(len(candidate_docs))
                    if bm25_raw_scores[i] > 0
                ]
                bm25_candidates.sort(key=lambda x: x[1], reverse=True)
                bm25_ranked_docs = bm25_candidates[:search_k]
            except Exception as e:
                print(f"[VectorStore] BM25 indexing error: {e}")
                bm25_ranked_docs = []

        # 4. RECIPROCAL RANK FUSION (RRF)
        K_RRF = 60
        rrf_scores: dict[str, float] = {}
        doc_registry: dict[str, tuple[LangchainDocument, float, float]] = {}

        # Ghi nhận Rank từ Vector Search (weight = 1.0)
        for rank, (doc, vec_score) in enumerate(vector_ranked_docs, 1):
            key = f"{doc.metadata.get('document_id')}_{doc.metadata.get('chunk_index')}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (K_RRF + rank))
            doc_registry[key] = (doc, vec_score, 0.0)

        # Ghi nhận Rank từ BM25 Search (weight = 0.8)
        for rank, (doc, bm25_score) in enumerate(bm25_ranked_docs, 1):
            key = f"{doc.metadata.get('document_id')}_{doc.metadata.get('chunk_index')}"
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (0.8 / (K_RRF + rank))
            if key in doc_registry:
                existing_doc, existing_vec, _ = doc_registry[key]
                doc_registry[key] = (existing_doc, existing_vec, bm25_score)
            else:
                doc_registry[key] = (doc, 0.0, bm25_score)

        # 5. TÍNH ĐIỂM TỔNG HỢP & LỌC THEO THRESHOLD
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        max_bm25 = max([v[2] for v in doc_registry.values()] or [1.0]) or 1.0

        matched_results = []
        for key in sorted_keys:
            doc, vec_score, bm25_score = doc_registry[key]
            norm_bm25 = round(bm25_score / max_bm25, 4) if max_bm25 > 0 else 0.0

            if vec_score > 0 and bm25_score > 0:
                final_score = round(0.7 * vec_score + 0.3 * norm_bm25, 4)
            elif vec_score > 0:
                final_score = round(vec_score, 4)
            else:
                final_score = round(0.4 + 0.4 * norm_bm25, 4)

            if similarity_threshold > 0 and final_score < similarity_threshold:
                continue

            matched_results.append({
                "document_id": doc.metadata.get("document_id"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": final_score,
                "vector_score": round(vec_score, 4),
                "bm25_score": round(bm25_score, 4),
            })

            if len(matched_results) >= top_k:
                break

        return matched_results
