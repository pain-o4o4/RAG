import os
import uuid
import json
import hashlib
import time
from typing import Optional, Any
import numpy as np

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

            test_d = len(self.embeddings.embed_query("test"))
            if index.d != test_d:
                print(f"[VectorStore] Old index d ({index.d}) != embedding d ({test_d}). Re-embedding docs...")
                docs = [
                    LangchainDocument(
                        page_content=m.get("content", ""),
                        metadata={
                            "document_id": str(m.get("document_id", "")),
                            "chunk_index": m.get("chunk_index", i),
                            "page_number": m.get("metadata", {}).get("page_number", 1)
                        }
                    ) for i, m in enumerate(meta)
                ]
                vectorstore = FAISS.from_documents(docs, self.embeddings)
            else:
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

        # Tìm kiếm k lớn hơn để sau đó lọc threshold và doc_ids
        search_k = min(vectorstore.index.ntotal, max(top_k * 4, 10))
        
        try:
            results = vectorstore.similarity_search_with_relevance_scores(
                query,
                k=search_k,
                filter=filter_func if target_doc_ids else None
            )
        except Exception:
            raw_results = vectorstore.similarity_search_with_score(
                query,
                k=search_k,
                filter=filter_func if target_doc_ids else None
            )
            # Chuyển đổi khoảng cách L2 sang điểm tương đồng 0.0 - 1.0
            results = [(doc, 1.0 / (1.0 + max(0.0, float(score)))) for doc, score in raw_results]

        matched_results = []
        for doc, score in results:
            float_score = float(score)
            if similarity_threshold > 0 and float_score < similarity_threshold:
                continue

            matched_results.append({
                "document_id": doc.metadata.get("document_id"),
                "chunk_index": doc.metadata.get("chunk_index"),
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": round(float_score, 4)
            })

            if len(matched_results) >= top_k:
                break

        return matched_results
