import os
import json
import uuid
from typing import Optional, Any
import numpy as np
import faiss

from app.core.config import settings

EMBEDDING_DIMENSION = 768


class VectorStore:
    """
    Quản lý Vector Database sử dụng thư viện FAISS (Facebook AI Similarity Search):
    - Quản lý tách biệt chỉ mục vector cho từng User ({user_id}.index).
    - Sử dụng IndexFlatIP (Cosine Similarity trên vector đã chuẩn hóa L2).
    - Lưu trữ metadata mapping giữa vector_id trong FAISS và bản ghi DocumentChunk trong Database.
    """

    def __init__(self, vector_dir: str = settings.VECTOR_STORE_DIR):
        self.vector_dir = vector_dir
        os.makedirs(self.vector_dir, exist_ok=True)

    def _get_index_path(self, user_id: uuid.UUID) -> str:
        return os.path.join(self.vector_dir, f"{str(user_id)}.index")

    def _get_meta_path(self, user_id: uuid.UUID) -> str:
        return os.path.join(self.vector_dir, f"{str(user_id)}_meta.json")

    def _load_index_and_meta(self, user_id: uuid.UUID) -> tuple[faiss.IndexFlatIP, list[dict[str, Any]]]:
        """Tải hoặc khởi tạo mới index FAISS và file metadata của user."""
        index_path = self._get_index_path(user_id)
        meta_path = self._get_meta_path(user_id)

        if os.path.exists(index_path) and os.path.exists(meta_path):
            index = faiss.read_index(index_path)
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return index, meta
        else:
            index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
            return index, []

    def _save_index_and_meta(
        self,
        user_id: uuid.UUID,
        index: faiss.IndexFlatIP,
        meta: list[dict[str, Any]]
    ) -> None:
        """Lưu trữ chỉ mục FAISS và metadata ra ổ đĩa."""
        index_path = self._get_index_path(user_id)
        meta_path = self._get_meta_path(user_id)

        faiss.write_index(index, index_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def add_chunks(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]]
    ) -> list[str]:
        """
        Nạp danh sách vector của tài liệu vào chỉ mục FAISS:
        - Chuẩn hóa L2 vector.
        - Thêm vector vào FAISS index.
        - Lưu trữ mapping metadata.
        - Trả về danh sách vector_id.
        """
        if not chunks or not embeddings:
            return []

        index, meta = self._load_index_and_meta(user_id)

        # Chuyển đổi thành ma trận numpy float32
        vec_np = np.array(embeddings, dtype=np.float32)
        # L2 normalize
        faiss.normalize_L2(vec_np)

        # Thêm vào FAISS
        index.add(vec_np)

        vector_ids = []
        for i, chunk in enumerate(chunks):
            v_id = f"vec_{uuid.uuid4().hex[:12]}"
            vector_ids.append(v_id)
            meta.append({
                "vector_id": v_id,
                "document_id": str(document_id),
                "chunk_index": chunk.get("chunk_index", i),
                "content": chunk.get("content", ""),
                "metadata": chunk.get("metadata", {}),
            })

        self._save_index_and_meta(user_id, index, meta)
        return vector_ids

    def search(
        self,
        user_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 4,
        document_id: Optional[uuid.UUID] = None,
        document_ids: Optional[list[uuid.UUID]] = None,
        similarity_threshold: float = settings.SIMILARITY_THRESHOLD
    ) -> list[dict[str, Any]]:
        """
        Truy vấn tương đồng ngữ nghĩa trong FAISS:
        - Lấy top_k kết quả có Cosine Similarity cao nhất.
        - Lọc theo similarity_threshold để chống Hallucination (bịa đặt thông tin).
        - Lọc theo document_id hoặc danh sách document_ids (tập hợp tài liệu trong phiên chat).
        """
        index_path = self._get_index_path(user_id)
        if not os.path.exists(index_path):
            return []

        index, meta = self._load_index_and_meta(user_id)
        if index.ntotal == 0 or not meta:
            return []

        # Chuẩn hóa vector câu hỏi
        query_np = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_np)

        # Tìm kiếm trong FAISS
        search_k = min(len(meta), top_k * 4)  # Lấy dôi ra để lọc theo document_id
        distances, indices = index.search(query_np, search_k)

        matched_results = []
        doc_id_str = str(document_id) if document_id else None
        target_doc_ids: Optional[set[str]] = None
        if document_ids:
            target_doc_ids = {str(d) for d in document_ids}
        elif doc_id_str:
            target_doc_ids = {doc_id_str}

        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(meta):
                continue

            # Kiểm tra ngưỡng tương đồng Cosine Similarity
            if float(score) < similarity_threshold:
                continue

            item = meta[idx]
            # Nếu người dùng chọn chat với danh sách tài liệu cụ thể
            if target_doc_ids is not None and item.get("document_id") not in target_doc_ids:
                continue

            matched_results.append({
                "vector_id": item.get("vector_id"),
                "document_id": item.get("document_id"),
                "chunk_index": item.get("chunk_index"),
                "content": item.get("content"),
                "metadata": item.get("metadata"),
                "score": float(score)
            })

            if len(matched_results) >= top_k:
                break

        return matched_results
