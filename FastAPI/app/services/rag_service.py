import uuid
import warnings
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

warnings.filterwarnings("ignore", message=".*automatic function calling.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*Automatic function calling.*", category=UserWarning)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.services.vector_store import VectorStore
from app.services.tool_service import ToolService
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
    RAG Service thông minh tích hợp Tool Calling chuẩn LangChain:
    - Bước 1 (Intent & Decision): LLM phân tích xem có cần tra cứu tài liệu hay không.
    - Nhánh A (Chào hỏi/Xã giao): Trả lời trực tiếp ngay, không tốn tài nguyên tìm kiếm FAISS.
    - Nhánh B (Tra cứu tri thức): Kích hoạt tool 'search_knowledge_base' -> Lấy Chunks -> Tổng hợp phản hồi có trích dẫn.
    - Đảm bảo Zero-Loop: Luồng 2 bước dứt khoát, không lặp vô tận.
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

    def _build_intent_messages(
        self,
        query: str,
        chat_history: Optional[list[dict]] = None
    ) -> list:
        """Xây dựng danh sách message để LLM phân tích ý định và quyết định gọi Tool."""
        system_prompt = (
            "Bạn là trợ lý AI thông minh chuyên nghiệp hỗ trợ giải đáp thắc mắc và phân tích tài liệu.\n"
            "- Nếu người dùng chào hỏi, cảm ơn hoặc hỏi kiến thức thông thường: Hãy trả lời trực tiếp, thân thiện và KHÔNG gọi công cụ.\n"
            "- Nếu người dùng hỏi về tài liệu, quy chế, chính sách, hợp đồng, số liệu nội bộ: HÃY GỌI công cụ 'search_knowledge_base' để tra cứu thông tin chính xác."
        )
        messages = [SystemMessage(content=system_prompt)]

        if chat_history:
            for m in chat_history[-4:]:
                role = m.get("role")
                content = m.get("content", "").strip()
                if content:
                    if role == "user":
                        messages.append(HumanMessage(content=content[:300]))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content[:300]))

        messages.append(HumanMessage(content=query))
        return messages

    def _build_rag_prompt(
        self,
        query: str,
        context_text: str,
        chat_history: Optional[list[dict]] = None
    ) -> str:
        """Xây dựng prompt tổng hợp câu trả lời dựa trên các đoạn trích xuất từ Tool."""
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
            "QUY TẮC PHẢN HỒI BẮT BUỘC:\n"
            "1. CHỐNG ẢO GIÁC (ZERO-HALLUCINATION): Chỉ sử dụng thông tin có trong các đoạn trích ở trên. Không tự ý bịa đặt.\n"
            "2. ĐỘ CHI TIẾT VÀ CẤU TRÚC: Khai thác triệt để các dữ kiện, trình bày Markdown đẹp mắt với tiêu đề và danh sách gạch đầu dòng rõ ràng.\n"
            "3. TRÍCH DẪN: Nêu rõ tên tài liệu và số trang tương ứng khi đưa ra số liệu/quy định.\n\n"
            f"Câu hỏi của người dùng: {query}"
        )

    async def query(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ) -> RAGResult:
        """Hàm đồng bộ xử lý câu hỏi: Quyết định gọi Tool -> Thực thi -> Sinh câu trả lời."""
        tool_service = ToolService(self.db, self.vector_store, user_id)
        tools = tool_service.get_tools()
        tool_map = {t.name: t for t in tools}
        llm_with_tools = self.llm.bind_tools(tools)

        intent_messages = self._build_intent_messages(query, chat_history)

        # LƯỢT 1: Phân tích Intent
        first_step = await llm_with_tools.ainvoke(intent_messages)

        # Nhánh A: Không cần gọi tool (Chào hỏi / Chat thông thường)
        if not first_step.tool_calls:
            answer = self._extract_text(first_step.content)
            return RAGResult(
                answer=answer,
                sources=[],
                model_name=settings.LLM_MODEL
            )

        # Nhánh B: Có yêu cầu gọi tool tra cứu tài liệu
        for tc in first_step.tool_calls:
            t_name = tc["name"]
            t_args = tc.get("args", {})
            if t_name in tool_map:
                if t_name == "search_knowledge_base" and "document_ids" not in t_args and document_ids:
                    t_args["document_ids"] = [str(d) for d in document_ids]
                obs = await tool_map[t_name].ainvoke(t_args)
            else:
                obs = ""

        # LƯỢT 2: Tổng hợp câu trả lời từ ngữ cảnh đã tra cứu
        sources = tool_service.retrieved_sources
        if not sources:
            return RAGResult(
                answer=(
                    "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                    "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
                ),
                sources=[],
                model_name=settings.LLM_MODEL
            )

        prompt = self._build_rag_prompt(query, obs, chat_history=chat_history)
        final_response = await self.llm.ainvoke(prompt)
        final_answer = self._extract_text(final_response.content)

        return RAGResult(
            answer=final_answer,
            sources=sources,
            model_name=settings.LLM_MODEL
        )

    async def stream_query(
        self,
        query: str,
        user_id: uuid.UUID,
        document_ids: Optional[list[uuid.UUID]] = None,
        chat_history: Optional[list[dict]] = None,
    ):
        """
        Luồng sinh phản hồi dạng Streaming qua Server-Sent Events:
        - Nhánh A (Chào hỏi): Bắn sources rỗng ngay -> Stream câu trả lời trực tiếp.
        - Nhánh B (Tra cứu): Gọi Tool -> Bắn sources ngay -> Stream câu trả lời tổng hợp.
        """
        tool_service = ToolService(self.db, self.vector_store, user_id)
        tools = tool_service.get_tools()
        tool_map = {t.name: t for t in tools}
        llm_with_tools = self.llm.bind_tools(tools)

        intent_messages = self._build_intent_messages(query, chat_history)

        try:
            first_step = await llm_with_tools.ainvoke(intent_messages)
        except Exception as e:
            yield {"type": "sources", "data": []}
            yield {"type": "token", "content": f"Lỗi kết nối mô hình AI: {str(e)}"}
            yield {"type": "done"}
            return

        # Nhánh A: Trả lời trực tiếp (Không có Tool Call)
        if not first_step.tool_calls:
            yield {"type": "sources", "data": []}
            direct_answer = self._extract_text(first_step.content)
            if direct_answer:
                yield {"type": "token", "content": direct_answer}
            yield {"type": "done"}
            return

        # Nhánh B: Thực thi Tool tra cứu tài liệu
        obs = ""
        for tc in first_step.tool_calls:
            t_name = tc["name"]
            t_args = tc.get("args", {})
            if t_name in tool_map:
                if t_name == "search_knowledge_base" and "document_ids" not in t_args and document_ids:
                    t_args["document_ids"] = [str(d) for d in document_ids]
                obs = await tool_map[t_name].ainvoke(t_args)

        # 1. Bắn danh sách sources về UI ngay lập tức
        sources = tool_service.retrieved_sources
        yield {"type": "sources", "data": sources}

        if not sources or not obs:
            no_info_msg = (
                "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
            )
            yield {"type": "token", "content": no_info_msg}
            yield {"type": "done"}
            return

        # 2. Stream từng token của câu trả lời tổng hợp
        prompt = self._build_rag_prompt(query, obs, chat_history=chat_history)
        try:
            async for chunk in self.llm.astream(prompt):
                token_text = self._extract_text(chunk.content)
                if token_text:
                    yield {"type": "token", "content": token_text}
        except Exception as e:
            fallback_msg = f"Lỗi trong quá trình sinh câu trả lời: {str(e)}"
            yield {"type": "token", "content": fallback_msg}

        yield {"type": "done"}
