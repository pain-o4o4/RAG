import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.tools import tool

from app.schemas.tool import KnowledgeSearchInput
from app.services.vector_store import VectorStore
from app.models.document import Document
from app.core.config import settings


class ToolService:
    """
    Quản lý các Tools tra cứu tài liệu dành riêng cho RAG:
    - search_knowledge_base: Tra cứu kho tài liệu FAISS kết hợp truy vấn PostgreSQL.
    - Quản lý danh sách trích dẫn (retrieved_sources) để hiển thị trên UI.
    """

    def __init__(self, db: AsyncSession, vector_store: VectorStore, user_id: uuid.UUID):
        self.db = db
        self.vector_store = vector_store
        self.user_id = user_id
        self.retrieved_sources: list[dict] = []

    def get_tools(self) -> list:
        """Tạo danh sách LangChain Tools sẵn sàng để bind vào LLM."""

        @tool("search_knowledge_base", args_schema=KnowledgeSearchInput)
        async def search_knowledge_base(
            query: str,
            document_ids: Optional[list[str]] = None
        ) -> str:
            """
            Tra cứu thông tin, dữ liệu, quy chế, điều khoản hoặc nội dung trong kho tài liệu đã tải lên của người dùng.
            Sử dụng công cụ này khi người dùng hỏi về kiến thức chuyên biệt, tài liệu nội bộ, số liệu cụ thể.
            KHÔNG sử dụng cho các câu chào hỏi xã giao, cảm ơn, hoặc kiến thức đời sống phổ thông.
            """
            doc_uuids = None
            if document_ids:
                doc_uuids = [uuid.UUID(str(d)) for d in document_ids if d]

            # 1. Tìm kiếm trong FAISS
            matched = self.vector_store.search(
                user_id=self.user_id,
                query=query,
                top_k=settings.TOP_K_RESULTS,
                document_ids=doc_uuids,
                similarity_threshold=settings.SIMILARITY_THRESHOLD,
            )

            if not matched:
                return "Không tìm thấy đoạn văn bản nào phù hợp trong kho tài liệu cho câu hỏi này."

            # 2. Truy vấn Database lấy tên tệp
            doc_ids = []
            for m in matched:
                d_id = m.get("document_id")
                if d_id:
                    try:
                        doc_ids.append(uuid.UUID(str(d_id)))
                    except ValueError:
                        pass

            doc_names = {}
            if doc_ids:
                docs_query = select(Document.id, Document.filename).where(
                    Document.id.in_(doc_ids),
                    Document.is_deleted == False
                )
                docs_res = await self.db.execute(docs_query)
                for d_id, d_name in docs_res.all():
                    doc_names[str(d_id)] = d_name

            # 3. Định dạng kết quả và lưu vết sources
            formatted_chunks = []
            for m in matched:
                d_id = str(m.get("document_id", ""))
                if d_id not in doc_names:
                    continue

                d_name = doc_names[d_id]
                page_num = m.get("metadata", {}).get("page_number", 1)
                snippet = m.get("content", "")
                score = round(m.get("score", 0.0), 3)

                source_item = {
                    "document_id": d_id,
                    "document_name": d_name,
                    "chunk_index": m.get("chunk_index"),
                    "similarity_score": score,
                    "page": page_num,
                    "snippet": snippet[:250] + ("..." if len(snippet) > 250 else ""),
                }
                self.retrieved_sources.append(source_item)

                formatted_chunks.append(
                    f"[Tài liệu: '{d_name}', Trang {page_num}]:\n{snippet}"
                )

            if not formatted_chunks:
                return "Không tìm thấy đoạn trích dẫn khả dụng (tài liệu có thể đã bị xóa)."

            return "\n\n---\n\n".join(formatted_chunks)

        return [search_knowledge_base]
