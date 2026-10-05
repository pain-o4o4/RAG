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
            docs_query = select(Document.id, Document.filename).where(
                Document.id.in_(doc_ids),
                Document.is_deleted == False
            )
            docs_res = await self.db.execute(docs_query)
            for d_id, d_name in docs_res.all():
                doc_names[str(d_id)] = d_name

        # 4. Đóng gói danh sách trích dẫn (sources)
        sources = []
        context_blocks = []

        for i, m in enumerate(matched, 1):
            d_id = str(m.get("document_id", ""))
            # Bỏ qua nếu tài liệu đã bị xóa mềm trong database
            if d_id not in doc_names:
                continue

            d_name = doc_names[d_id]
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
                f"[Trích đoạn {len(sources)} - Tài liệu: '{d_name}', Trang {page_num} (Độ tương đồng: {score})]:\n{snippet}"
            )

        if not sources:
            return [], ""

        context_text = "\n\n".join(context_blocks)
        return sources, context_text

    def build_prompt(self, query: str, context_text: str, chat_history: Optional[list[dict]] = None) -> str:
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
            "Bạn là chuyên gia phân tích nghiệp vụ và trợ lý AI cao cấp. "
            "Nhiệm vụ của bạn là giải đáp câu hỏi của người dùng một cách CHI TIẾT, TOÀN DIỆN và CHUYÊN NGHIỆP dựa trên tài liệu được cung cấp.\n\n"
            f"{history_text}"
            "DƯỚI ĐÂY LÀ CÁC ĐOẠN TRÍCH TỪ TÀI LIỆU:\n"
            "---------------------\n"
            f"{context_text}\n"
            "---------------------\n\n"
            "QUY TẮC PHẢN HỒI BẮT BUỘC (TUÂN THỦ TUYỆT ĐỐI):\n"
            "1. TÍNH CHÍNH XÁC & CHỐNG ẢO GIÁC (ZERO-HALLUCINATION):\n"
            "   - CHỈ sử dụng thông tin và dữ kiện có trong các đoạn trích tài liệu ở trên.\n"
            "   - Tuyệt đối KHÔNG tự ý bịa đặt, phỏng đoán hoặc bổ sung kiến thức ngoài tài liệu.\n"
            "   - Nếu tài liệu hoàn toàn không có thông tin hoặc không đủ căn cứ, hãy nêu rõ ràng: 'Tài liệu được cung cấp không chứa đủ thông tin để trả lời chi tiết phần này.'\n\n"
            "2. ĐỘ CHI TIẾT VÀ CẤU TRÚC PHÂN TÍCH:\n"
            "   - Khai thác TRIỆT ĐỂ mọi thông tin có trong các đoạn trích. Tránh trả lời sơ sài hoặc tóm tắt quá ngắn.\n"
            "   - Với mỗi chức năng / quy trình, hãy phân tích đầy đủ các góc độ nếu tài liệu có đề cập: Mục đích, Tác nhân (Actor), Tiền điều kiện, Hậu điều kiện, Các bước trong luồng xử lý (Flow of events), và Dữ liệu liên quan.\n"
            "   - Trình bày dạng Markdown đẹp mắt: Sử dụng tiêu đề (###), danh sách gạch đầu dòng rõ ràng, bảng biểu (nếu có so sánh) và trích dẫn rõ số trang / tên tài liệu tương ứng.\n\n"
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
                "gemini-3.7-flash",
                "gemini-3.8-flash",
                "gemini-3.5-flash",
                "gemini-flash-latest",
            ]
            seen = set()
            ordered_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            last_error = None
            for m in ordered_models:
                try:
                    response = await client.aio.models.generate_content(
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
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> RAGResult:
        """Hàm chính điều phối toàn bộ quy trình RAG: Retrieval qua FAISS -> Generation qua Gemini."""
        sources, context_text = await self.retrieve_context(
            query=query,
            user_id=user_id,
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

    async def stream_query(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ):
        """
        Luồng sinh phản hồi dạng Server-Sent Events (SSE) theo thời gian thực:
        1. Retrieval qua FAISS (kèm bộ lọc threshold và document_ids).
        2. Phát sự kiện `sources` chứa danh sách trích dẫn.
        3. Phát từng sự kiện `token` khi Gemini sinh từng từ (streaming typewriter).
        4. Phát sự kiện `done` báo hiệu kết thúc.
        """
        import json

        sources, context_text = await self.retrieve_context(
            query=query,
            user_id=user_id,
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
                    document_ids=document_ids,
                )
                if aug_sources:
                    sources, context_text = aug_sources, aug_context

        # 1. Phát sự kiện sources đầu tiên
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        if not context_text or not sources:
            no_info_msg = (
                "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
            )
            yield f"event: token\ndata: {json.dumps({'text': no_info_msg})}\n\n"
            yield f"event: done\ndata: [DONE]\n\n"
            return

        # 2. Xây dựng prompt
        prompt = self.build_prompt(query, context_text, chat_history=chat_history)
        is_real_gemini_key = (
            settings.GEMINI_API_KEY 
            and "your_gemini_api" not in settings.GEMINI_API_KEY.lower()
        )

        if is_real_gemini_key:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            models_to_try = [
                settings.LLM_MODEL,
                "gemini-flash-lite-latest",
                "gemini-3.6-flash",
            ]
            seen = set()
            ordered_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            stream_success = False
            last_err = None

            for m in ordered_models:
                try:
                    response_stream = await client.aio.models.generate_content_stream(
                        model=m,
                        contents=prompt,
                    )
                    async for chunk in response_stream:
                        if chunk and hasattr(chunk, "text") and chunk.text:
                            yield f"event: token\ndata: {json.dumps({'text': chunk.text})}\n\n"
                    stream_success = True
                    break
                except Exception as e:
                    last_err = e
                    continue

            if not stream_success:
                fallback_msg = f"Lỗi kết nối tới mô hình AI: {str(last_err)}"
                yield f"event: token\ndata: {json.dumps({'text': fallback_msg})}\n\n"
        else:
            top_source = sources[0]
            simulated_text = (
                f"Dựa trên tài liệu '{top_source['document_name']}' (Trang {top_source['page']}):\n\n"
                f"\"{top_source['snippet']}\""
            )
            words = simulated_text.split(" ")
            for w in words:
                yield f"event: token\ndata: {json.dumps({'text': w + ' '})}\n\n"

        yield f"event: done\ndata: [DONE]\n\n"
