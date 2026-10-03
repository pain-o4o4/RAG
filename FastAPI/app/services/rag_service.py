import uuid
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.core.config import settings


@dataclass
class RAGResult:
    """Đối tượng kết quả trả về từ RAG Engine."""
    answer: str
    sources: Optional[list[dict]] = None
    model_name: str = settings.LLM_MODEL
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class RAGService:
    """
    RAG Service độc lập:
    - Triển khai toàn bộ quy trình: Vector Embedding -> FAISS Retrieval -> Threshold Filtering -> LLM Generation.
    - Xử lý triệt để bài toán chống Hallucination (tự động thông báo khi tài liệu không có thông tin phù hợp).
    - Cung cấp nguồn trích dẫn cụ thể (tên tài liệu, trang, snippet, điểm tương đồng).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = VectorStore()

    async def retrieve_context(
        self,
        query: str,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
        document_ids: Optional[list[uuid.UUID]] = None,
        top_k: int = settings.TOP_K_RESULTS,
        threshold: float = settings.SIMILARITY_THRESHOLD
    ) -> tuple[list[dict], str]:
        """
        Giai đoạn 1: Retrieval (Truy xuất qua Vector Database FAISS)
        1. Tạo vector embedding cho câu hỏi của người dùng.
        2. Tìm kiếm các vector gần nhất trong FAISS index của user.
        3. Áp dụng ngưỡng similarity_threshold để loại bỏ kết quả không liên quan.
        4. Truy vấn Database lấy tên tệp tương ứng.
        """
        # 1. Vector hóa câu hỏi
        query_vec = EmbeddingService.get_embedding(query)

        # 2. Tìm kiếm trong FAISS
        matched = self.vector_store.search(
            user_id=user_id,
            query_embedding=query_vec,
            top_k=top_k,
            document_id=document_id,
            document_ids=document_ids,
            similarity_threshold=threshold,
        )

        if not matched:
            return [], ""

        # 3. Lấy tên tệp tin tương ứng từ DB
        doc_ids = []
        for m in matched:
            d_id = m.get("document_id")
            if d_id:
                try:
                    doc_ids.append(uuid.UUID(d_id))
                except ValueError:
                    pass

        doc_names = {}
        if doc_ids:
            docs_query = select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
            docs_res = await self.db.execute(docs_query)
            for d_id, d_name in docs_res.all():
                doc_names[str(d_id)] = d_name

        # 4. Đóng gói danh sách trích dẫn (sources)
        sources = []
        context_blocks = []

        for i, m in enumerate(matched, 1):
            d_id = m.get("document_id", "")
            d_name = doc_names.get(d_id, "Tài liệu không xác định")
            page_num = m.get("metadata", {}).get("page_number", 1)
            snippet = m.get("content", "")
            score = round(m.get("score", 0.0), 3)

            sources.append({
                "document_id": d_id,
                "document_name": d_name,
                "chunk_index": m.get("chunk_index"),
                "similarity_score": score,
                "page": page_num,
                "snippet": snippet[:250] + ("..." if len(snippet) > 250 else ""),
            })

            context_blocks.append(
                f"[Trích đoạn {i} - Tài liệu: '{d_name}', Trang {page_num} (Độ tương đồng: {score})]:\n{snippet}"
            )

        context_text = "\n\n".join(context_blocks)
        return sources, context_text

    def build_prompt(self, query: str, context_text: str) -> str:
        """Xây dựng Prompt chặt chẽ theo nguyên tắc RAG chống Hallucination."""
        return (
            "Bạn là trợ lý AI chuyên nghiệp phân tích tài liệu và trả lời câu hỏi (RAG Assistant).\n"
            "Dưới đây là các đoạn thông tin trích xuất từ tài liệu của người dùng:\n"
            "---------------------\n"
            f"{context_text}\n"
            "---------------------\n\n"
            "YÊU CẦU QUAN TRỌNG ĐỐI VỚI CÂU TRẢ LỜI:\n"
            "1. CHỈ sử dụng các thông tin có trong đoạn trích dẫn ở trên để trả lời. Tuyệt đối không được bịa đặt hay suy đoán thông tin ngoài ngữ cảnh.\n"
            "2. Khi trích dẫn thông tin, hãy nêu rõ tên tài liệu và số trang (ví dụ: 'Theo tài liệu ABC, trang X...').\n"
            "3. Nếu nội dung trích dẫn không đủ hoặc không chứa câu trả lời, hãy trả lời thẳng thắn: 'Tài liệu không cung cấp đủ thông tin để trả lời câu hỏi này.'\n\n"
            f"Câu hỏi của người dùng: {query}"
        )

    async def generate_answer(self, query: str, context_text: str, sources: list[dict]) -> RAGResult:
        """
        Giai đoạn 2: Generation (Sinh phản hồi qua Google Gemini API với cơ chế tự động thử đa mô hình)
        """
        if not context_text or not sources:
            return RAGResult(
                answer=(
                    "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                    "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
                ),
                sources=[],
                model_name=settings.LLM_MODEL,
            )

        prompt = self.build_prompt(query, context_text)
        is_real_gemini_key = (
            settings.GEMINI_API_KEY 
            and "your_gemini_api" not in settings.GEMINI_API_KEY.lower()
        )

        ai_content = ""
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        used_model = settings.LLM_MODEL

        if is_real_gemini_key:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            models_to_try = [
                settings.LLM_MODEL,
                "gemini-flash-latest",
                "gemini-3.7-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
            ]
            seen = set()
            ordered_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            last_error = None
            for m in ordered_models:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=prompt,
                    )
                    if response and response.text:
                        ai_content = response.text
                        used_model = m
                        if hasattr(response, "usage_metadata") and response.usage_metadata:
                            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
                            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", None)
                            total_tokens = getattr(response.usage_metadata, "total_token_count", None)
                        last_error = None
                        break
                except Exception as e:
                    last_error = e

            if not ai_content and last_error:
                ai_content = f"Lỗi kết nối tới mô hình AI ({used_model}): {str(last_error)}"
        else:
            top_source = sources[0]
            ai_content = (
                f"Dựa trên tài liệu '{top_source['document_name']}' (Trang {top_source['page']}):\n\n"
                f"\"{top_source['snippet']}\"\n\n"
                f"[Lưu ý: Để kích hoạt khả năng tổng hợp và suy luận trực tiếp từ Google Gemini ({settings.LLM_MODEL}), "
                f"vui lòng điền GEMINI_API_KEY hợp lệ vào file .env]."
            )

        return RAGResult(
            answer=ai_content,
            sources=sources,
            model_name=used_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def query(
        self,
        query: str,
        user_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
        document_ids: Optional[list[uuid.UUID]] = None,
    ) -> RAGResult:
        """Hàm chính điều phối toàn bộ quy trình RAG: Retrieval qua FAISS -> Generation qua Gemini."""
        sources, context_text = await self.retrieve_context(
            query=query,
            user_id=user_id,
            document_id=document_id,
            document_ids=document_ids,
        )
        return await self.generate_answer(query=query, context_text=context_text, sources=sources)
