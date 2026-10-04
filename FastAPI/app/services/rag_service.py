import uuid
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
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
        # Tìm kiếm trực tiếp trong FAISS (VectorStore tự xử lý text embedding)
        matched = self.vector_store.search(
            user_id=user_id,
            query=query,
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

    def build_prompt(self, query: str, context_text: str, chat_history: Optional[list[dict]] = None) -> str:
        """Xây dựng Prompt RAG linh hoạt, kết hợp tài liệu và kiến thức sẵn có."""
        history_text = ""
        if chat_history:
            formatted_turns = []
            for m in chat_history[-4:]:
                sender = "Người dùng" if m.get("role") == "user" else "Trợ lý AI"
                content = m.get("content", "").strip()
                if content:
                    formatted_turns.append(f"{sender}: {content[:300]}")
            if formatted_turns:
                history_text = "LỊCH SỬ TRAO ĐỔI GẦN ĐÂY:\n" + "\n".join(formatted_turns) + "\n\n"

        return (
            "Bạn là trợ lý AI chuyên nghiệp hỗ trợ phân tích tài liệu và giải đáp câu hỏi của người dùng một cách chi tiết và sâu sắc.\n"
            f"{history_text}"
            "Dưới đây là các thông tin trích xuất từ tài liệu liên quan:\n"
            "---------------------\n"
            f"{context_text}\n"
            "---------------------\n\n"
            "HƯỚNG DẪN TRẢ LỜI:\n"
            "1. Hãy phân tích kỹ câu hỏi và đưa ra câu trả lời **thật chi tiết, sâu sắc và đầy đủ**, dựa vào thông tin từ tài liệu được cung cấp.\n"
            "2. Nếu tài liệu không đủ ý, bạn **ĐƯỢC PHÉP kết hợp với kiến thức sẵn có** của mình để giải thích thêm, mở rộng vấn đề, hoặc cung cấp bối cảnh sâu sắc hơn. Tuy nhiên, hãy phân biệt rõ đâu là thông tin từ tài liệu, đâu là kiến thức bổ sung của bạn.\n"
            "3. Khi sử dụng thông tin từ tài liệu, hãy trích dẫn rõ nguồn (tên tài liệu, trang) để tăng độ tin cậy.\n"
            "4. Về định dạng: Dùng định dạng Markdown chuẩn. Với danh sách liệt kê, hãy dùng ký tự gạch đầu dòng '-' (không dùng ký tự bullet '•' hay '●') và không để dòng trống thừa giữa các mục danh sách để trình bày thật gọn gàng, đẹp mắt.\n"
            "5. Nếu người dùng yêu cầu phân tích chi tiết hơn hoặc cảm thấy câu trả lời trước đó quá ngắn/sơ sài, hãy đi sâu vào từng khía cạnh kiến trúc, kỹ thuật, dữ liệu, giải pháp công nghệ một cách thấu đáo.\n\n"
            f"Câu hỏi của người dùng: {query}"
        )

    async def generate_answer(
        self,
        query: str,
        context_text: str,
        sources: list[dict],
        chat_history: Optional[list[dict]] = None
    ) -> RAGResult:
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

        prompt = self.build_prompt(query, context_text, chat_history=chat_history)
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
                "gemini-3.8-flash",
                "gemini-3.7-flash",
                "gemini-3.5-flash",
                "gemini-flash-lite-latest",
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
        chat_history: Optional[list[dict]] = None,
    ) -> RAGResult:
        """Hàm chính điều phối toàn bộ quy trình RAG: Retrieval qua FAISS -> Generation qua Gemini."""
        sources, context_text = await self.retrieve_context(
            query=query,
            user_id=user_id,
            document_id=document_id,
            document_ids=document_ids,
        )

        # Nếu chưa tìm thấy kết quả và có lịch sử hội thoại, thử kết hợp với câu hỏi trước
        if (not sources or len(sources) == 0) and chat_history:
            prev_user_queries = [m["content"] for m in chat_history if m.get("role") == "user"]
            if prev_user_queries:
                augmented_query = f"{prev_user_queries[-1]} {query}"
                aug_sources, aug_context = await self.retrieve_context(
                    query=augmented_query,
                    user_id=user_id,
                    document_id=document_id,
                    document_ids=document_ids,
                )
                if aug_sources:
                    sources, context_text = aug_sources, aug_context

        return await self.generate_answer(
            query=query,
            context_text=context_text,
            sources=sources,
            chat_history=chat_history
        )
