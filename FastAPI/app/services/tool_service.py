import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.tools import tool

from app.schemas.tool import KnowledgeSearchInput, ListUserDocumentsInput, WebSearchInput
from app.services.vector_store import VectorStore
from app.models.document import Document
from app.core.config import settings


class ToolService:
    """
    Quản lý các Tools tra cứu tài liệu và tri thức cho RAG Agent:
    - search_knowledge_base: Tra cứu kho tài liệu FAISS kết hợp truy vấn PostgreSQL.
    - list_user_documents: Tra cứu danh sách và trạng thái các tài liệu của người dùng.
    - web_search: Tìm kiếm thông tin trên Internet (chỉ bật khi enable_web_search=True).
    - Quản lý danh sách trích dẫn (retrieved_sources) để hiển thị trên UI.
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_store: VectorStore,
        user_id: uuid.UUID,
        enable_web_search: bool = False
    ):
        self.db = db
        self.vector_store = vector_store
        self.user_id = user_id
        self.enable_web_search = enable_web_search
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
            KHÔNG sử dụng cho các câu chào hỏi xã giao, cảm ơn, hoặc liệt kê danh sách file.
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
            for i, chunk in enumerate(matched,1):
                print("DEBUG: Chunk", i, ":", chunk)
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

            for idx, src in enumerate(self.retrieved_sources, 1):
                print(src)
            

            if not formatted_chunks:
                return "Không tìm thấy đoạn trích dẫn khả dụng (tài liệu có thể đã bị xóa)."

            return "\n\n---\n\n".join(formatted_chunks)

        @tool("list_user_documents", args_schema=ListUserDocumentsInput)
        async def list_user_documents(
            keyword: Optional[str] = None
        ) -> str:
            """
            Xem danh sách các tệp tài liệu mà người dùng đã tải lên hệ thống (tên file, định dạng, dung lượng, trạng thái).
            Sử dụng công cụ này khi người dùng hỏi các câu như: 'Tôi đã tải lên những file nào?', 'Tôi có tài liệu ABC không?', 'Danh sách tài liệu của tôi'.
            """
            query_stmt = select(Document).where(
                Document.user_id == self.user_id,
                Document.is_deleted == False
            )
            if keyword and keyword.strip():
                query_stmt = query_stmt.where(Document.filename.ilike(f"%{keyword.strip()}%"))

            query_stmt = query_stmt.order_by(Document.created_at.desc())
            res = await self.db.execute(query_stmt)
            docs = res.scalars().all()

            if not docs:
                if keyword:
                    return f"Người dùng chưa có tài liệu nào có tên chứa từ khóa '{keyword}'."
                return "Người dùng hiện chưa tải lên tài liệu nào trong hệ thống."

            lines = [f"Danh sách tài liệu người dùng đã tải lên ({len(docs)} tài liệu):"]
            for idx, d in enumerate(docs, 1):
                size_kb = round(d.file_size / 1024, 1) if d.file_size else 0
                created_str = d.created_at.strftime("%d/%m/%Y %H:%M") if d.created_at else "N/A"
                lines.append(
                    f"{idx}. {d.filename} (ID: {d.id}) | Định dạng: {d.file_type} | Dung lượng: {size_kb} KB | Số đoạn: {d.chunk_count} | Ngày tải: {created_str} | Trạng thái: {d.status}"
                )

            return "\n".join(lines)

        tools = [search_knowledge_base, list_user_documents]

        if self.enable_web_search:
            @tool("web_search", args_schema=WebSearchInput)
            async def web_search(query: str) -> str:
                """
                Tìm kiếm thông tin cập nhật trên Internet (Google / DuckDuckGo).
                Chỉ sử dụng khi người dùng yêu cầu tra cứu thông tin ngoài thế giới hoặc khi tài liệu nội bộ không chứa câu trả lời.
                """
                try:
                    from ddgs import DDGS
                    results = list(DDGS().text(query, max_results=5))
                except Exception:
                    try:
                        from duckduckgo_search import DDGS
                        results = list(DDGS().text(query, max_results=5))
                    except Exception as e:
                        return f"Lỗi khi tìm kiếm trên Internet: {str(e)}"

                web_snippets = []
                for r in results:
                    title = r.get("title", "")
                    url = r.get("href", "")
                    body = r.get("body", "")

                    self.retrieved_sources.append({
                        "type": "web",
                        "document_id": "web",
                        "document_name": title,
                        "url": url,
                        "snippet": body[:300] + ("..." if len(body) > 300 else ""),
                        "similarity_score": 1.0,
                    })
                    web_snippets.append(f"[Nguồn Web: '{title}'] ({url}):\n{body}")

                if not web_snippets:
                    return f"Không tìm thấy kết quả phù hợp trên Internet cho từ khóa: '{query}'."

                return "\n\n---\n\n".join(web_snippets)

            tools.append(web_search)

        return tools
