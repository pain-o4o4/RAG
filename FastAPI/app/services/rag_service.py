import uuid
import warnings
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

warnings.filterwarnings("ignore", message=".*automatic function calling.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*Automatic function calling.*", category=UserWarning)

from langchain_google_genai import ChatGoogleGenerativeAI
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
    RAG Service độc lập chuẩn 100% LangChain:
    - Triển khai toàn bộ quy trình: Vector Embedding -> FAISS Retrieval -> Threshold Filtering -> LLM Generation (ChatGoogleGenerativeAI).
    - Xử lý triệt để bài toán chống Hallucination (tự động thông báo khi tài liệu không có thông tin phù hợp).
    - Cung cấp nguồn trích dẫn cụ thể (tên tài liệu, trang, snippet, điểm tương đồng).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = VectorStore()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0,
        )

    @staticmethod
    def _extract_text(content) -> str:
        """Trích xuất chuỗi văn bản an toàn từ LangChain Message Content (hỗ trợ cả str và list[dict])."""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content or "")

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
        # In kiểm tra:
        print("\n" + "="*30 + " KẾT QUẢ RETRIEVE " + "="*30)
        for i, (source, block) in enumerate(zip(sources, context_blocks)):
            print(f"\n--- [Trích đoạn {i+1}] ---")
            print("SOURCE:", source)
            print("CONTEXT NỘI DUNG:\n", block)
        print("="*80 + "\n")

        return sources, context_text

    def build_prompt(
        self,
        query: str,
        context_text: str,
        chat_history: Optional[list[dict]] = None
    ) -> str:
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
        Giai đoạn 2: Generation (Sinh phản hồi qua LangChain ChatGoogleGenerativeAI)
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
        print("===================================")
        print("context gửi lên LLM bao gồm cả system prompt + lịch sử chat chứ không riêng chunk lấy ra được".capitalize(), prompt)
        print("===================================")

        ai_content = ""
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None

        try:
            response = await self.llm.ainvoke(prompt)
            ai_content = self._extract_text(response.content)
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = response.usage_metadata.get("input_tokens")
                completion_tokens = response.usage_metadata.get("output_tokens")
                total_tokens = response.usage_metadata.get("total_tokens")
        except Exception as e:
            ai_content = f"Lỗi kết nối tới mô hình AI ({settings.LLM_MODEL}): {str(e)}"

        return RAGResult(
            answer=ai_content,
            sources=sources,
            model_name=settings.LLM_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    async def _prepare_rag_context(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> tuple[list[dict], str, str]:
        """Gom nhóm logic Retrieval và Build Prompt dùng chung cho cả query và stream_query."""
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

        prompt = ""
        if context_text and sources:
            prompt = self.build_prompt(query, context_text, chat_history=chat_history)
            print("==================================================")
            print("context gửi lên LLM bao gồm cả system prompt + lịch sử chat chứ không riêng chunk lấy ra được \n".upper(), prompt)
            print("==================================================")

        return sources, context_text, prompt

    async def query(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> RAGResult:
        """Hàm chính điều phối toàn bộ quy trình RAG: Retrieval qua FAISS -> Generation qua Gemini."""
        sources, context_text, prompt = await self._prepare_rag_context(
            query=query,
            user_id=user_id,
            document_ids=document_ids,
            chat_history=chat_history
        )

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
        Luồng sinh phản hồi dạng Python Generator qua LangChain astream:
        1. Retrieval qua FAISS.
        2. Phát event `{'type': 'sources', 'data': sources}`.
        3. Phát từng event `{'type': 'token', 'content': chunk}` theo thời gian thực.
        4. Phát event `{'type': 'done'}` báo hiệu kết thúc.
        """
        sources, context_text, prompt = await self._prepare_rag_context(
            query=query,
            user_id=user_id,
            document_ids=document_ids,
            chat_history=chat_history
        )

        # 1. Phát sự kiện sources đầu tiên
        yield {"type": "sources", "data": sources}

        if not context_text or not sources:
            no_info_msg = (
                "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
            )
            yield {"type": "token", "content": no_info_msg}
            yield {"type": "done"}
            return

        try:
            async for chunk in self.llm.astream(prompt):
                token_text = self._extract_text(chunk.content)
                if token_text:
                    yield {"type": "token", "content": token_text}
        except Exception as e:
            fallback_msg = f"Lỗi kết nối tới mô hình AI: {str(e)}"
            yield {"type": "token", "content": fallback_msg}

        yield {"type": "done"}

