import uuid
import logging
import warnings
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

# Bỏ qua các cảnh báo nội bộ không ảnh hưởng từ thư viện google-genai
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

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
    RAG Service thông minh tích hợp Tool Calling & Cơ chế dự phòng (High Availability Fallback):
    - Tự động fallback sang mô hình nhẹ (gemini-3.5-flash-lite) khi mô hình chính gặp lỗi 503 / Quá tải.
    - Zero-Loop Architecture: 2 bước dứt khoát (Intent Routing -> Tool Execution -> Stream Response).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = VectorStore()
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0,
            max_retries=2,
        )
        self.fallback_llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.0,
            max_retries=2,
        )

    @staticmethod
    def _extract_text(content) -> str:
        """Trích xuất chuỗi văn bản an toàn từ LangChain Message Content."""
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
        chat_history: Optional[list[dict]] = None,
        enable_web_search: bool = False
    ) -> list:
        """Xây dựng danh sách message để LLM phân tích ý định và chọn công cụ."""
        web_instruction = (
            "- Nếu câu hỏi cần kiến thức thời sự, sự kiện ngoài đời sống mà tài liệu nội bộ không có: HÃY GỌI công cụ 'web_search'.\n"
            if enable_web_search else ""
        )
        system_prompt = (
            "Bạn là trợ lý AI phân tích tài liệu chuyên sâu.\n"
            "- CHỈ trả lời trực tiếp không dùng công cụ đối với các câu chào hỏi xã giao đơn thuần (như: 'xin chào', 'hello', 'cảm ơn', 'tạm biệt').\n"
            "- NGOẠI TRỪ chào hỏi, ĐỐI VỚI MỌI CÂU HỎI VỀ KIẾN THỨC, ĐỊNH NGHĨA, SỰ KIỆN, DỮ LIỆU: BẮT BUỘC PHẢI GỌI CÔNG CỤ 'search_knowledge_base' ĐỂ TÌM KIẾM TRONG TÀI LIỆU TRƯỚC."
            "- Nếu người dùng hỏi về nội dung, quy chế, chính sách, hợp đồng, số liệu trong tài liệu: HÃY GỌI công cụ 'search_knowledge_base'.\n"
            f"{web_instruction}"
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
        # print("DEBUG: Intent Messages:", messages)
        messages.append(HumanMessage(content=query))
        return messages

    def _build_synthesis_prompt(
        self,
        query: str,
        observation: str,
        tool_name: str,
        chat_history: Optional[list[dict]] = None
    ) -> str:
        """Xây dựng prompt tổng hợp câu trả lời dựa trên kết quả trả về từ công cụ."""
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

        if tool_name == "list_user_documents":
            return (
                "Bạn là trợ lý AI quản lý tài liệu. Dưới đây là thông tin danh sách tài liệu của người dùng được lấy từ cơ sở dữ liệu:\n"
                "---------------------\n"
                f"{observation}\n"
                "---------------------\n\n"
                f"{history_text}"
                f"Câu hỏi của người dùng: {query}\n\n"
                "YÊU CẦU: Trả lời người dùng một cách thân thiện, rõ ràng, định dạng danh sách Markdown đẹp mắt."
            )
        elif tool_name == "web_search":
            return (
                "Bạn là trợ lý AI thông minh và đáng tin cậy. Dưới đây là thông tin tìm kiếm được từ Internet:\n"
                "---------------------\n"
                f"{observation}\n"
                "---------------------\n\n"
                f"{history_text}"
                f"Câu hỏi của người dùng: {query}\n\n"
                "YÊU CẦU PHẢN HỒI:\n"
                "1. Tổng hợp và trả lời câu hỏi của người dùng một cách chính xác, mạch lạc và khách quan dựa trên thông tin tìm kiếm được.\n"
                "2. Trình bày rõ ràng, dễ hiểu bằng định dạng Markdown.\n"
                "3. Nếu thông tin tìm kiếm không đủ dữ liệu chi tiết, hãy trả lời dựa trên những gì thu thập được và giải thích ngắn gọn, không bịa đặt."
            )
        else:
            # Mặc định: search_knowledge_base (Tài liệu nội bộ)
            return (
                "Bạn là chuyên gia phân tích nghiệp vụ và trợ lý AI cao cấp. "
                "Nhiệm vụ của bạn là giải đáp câu hỏi của người dùng một cách CHI TIẾT, TOÀN DIỆN và CHUYÊN NGHIỆP dựa trên tài liệu được cung cấp.\n\n"
                f"{history_text}"
                "DƯỚI ĐÂY LÀ CÁC ĐOẠN TRÍCH TỪ TÀI LIỆU:\n"
                "---------------------\n"
                f"{observation}\n"
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
        enable_web_search: bool = False,
    ) -> RAGResult:
        """Hàm đồng bộ xử lý câu hỏi: Quyết định gọi Tool -> Thực thi -> Sinh câu trả lời (kèm Auto-fallback)."""
        tool_service = ToolService(self.db, self.vector_store, user_id, document_ids=document_ids, enable_web_search=enable_web_search)
        tools = tool_service.get_tools()
        tool_map = {t.name: t for t in tools}

        intent_messages = self._build_intent_messages(query, chat_history, enable_web_search=enable_web_search)

        # LƯỢT 1: Phân tích Intent với cơ chế fallback
        try:
            llm_with_tools = self.llm.bind_tools(tools)
            first_step = await llm_with_tools.ainvoke(intent_messages)
        except Exception:
            fallback_tools = self.fallback_llm.bind_tools(tools)
            first_step = await fallback_tools.ainvoke(intent_messages)

        # Nhánh A: Không cần gọi tool (Chào hỏi / Chat thông thường)
        if not first_step.tool_calls:
            answer = self._extract_text(first_step.content)
            return RAGResult(
                answer=answer,
                sources=[],
                model_name=settings.LLM_MODEL
            )

        # Nhánh B: Có yêu cầu gọi tool
        last_tool_name = ""
        obs = ""
        for tc in first_step.tool_calls:
            t_name = tc["name"]
            t_args = tc.get("args", {})
            last_tool_name = t_name
            if t_name in tool_map:
                obs = await tool_map[t_name].ainvoke(t_args)

        sources = tool_service.retrieved_sources

        # Nếu là tra cứu tài liệu nội bộ mà không tìm thấy đoạn nào
        if last_tool_name == "search_knowledge_base" and not sources:
            return RAGResult(
                answer=(
                    "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                    "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
                ),
                sources=[],
                model_name=settings.LLM_MODEL
            )

        # LƯỢT 2: Tổng hợp câu trả lời từ dữ liệu đã lấy (kèm Auto-fallback)
        prompt = self._build_synthesis_prompt(query, obs, last_tool_name, chat_history=chat_history)
        try:
            final_response = await self.llm.ainvoke(prompt)
        except Exception:
            final_response = await self.fallback_llm.ainvoke(prompt)

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
        enable_web_search: bool = False,
    ):
        """
        Luồng sinh phản hồi dạng Streaming qua Server-Sent Events (kèm Auto-fallback chống 503):
        - Nhánh A (Chào hỏi): Bắn sources rỗng ngay -> Stream câu trả lời trực tiếp.
        - Nhánh B (Tra cứu Tool): Gọi Tool -> Bắn sources ngay -> Stream câu trả lời tổng hợp.
        """
        tool_service = ToolService(self.db, self.vector_store, user_id, document_ids=document_ids, enable_web_search=enable_web_search)
        tools = tool_service.get_tools()
        tool_map = {t.name: t for t in tools}

        intent_messages = self._build_intent_messages(query, chat_history, enable_web_search=enable_web_search)

        # 1. Phân tích Intent với fallback
        try:
            llm_with_tools = self.llm.bind_tools(tools)
            first_step = await llm_with_tools.ainvoke(intent_messages)
        except Exception:
            try:
                fallback_tools = self.fallback_llm.bind_tools(tools)
                first_step = await fallback_tools.ainvoke(intent_messages)
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

        # Nhánh B: Thực thi Tool
        last_tool_name = ""
        obs = ""
        for tc in first_step.tool_calls:
            t_name = tc["name"]
            t_args = tc.get("args", {})
            last_tool_name = t_name
            if t_name in tool_map:
                obs = await tool_map[t_name].ainvoke(t_args)

        # 1. Bắn danh sách sources về UI ngay lập tức
        sources = tool_service.retrieved_sources
        yield {"type": "sources", "data": sources}

        # Nếu là tìm kiếm tài liệu nội bộ mà không có kết quả
        if last_tool_name == "search_knowledge_base" and not sources:
            no_info_msg = (
                "Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. "
                "Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."
            )
            yield {"type": "token", "content": no_info_msg}
            yield {"type": "done"}
            return

        # 2. Stream từng token của câu trả lời tổng hợp (kèm Auto-fallback nếu LLM chính bị 503)
        prompt = self._build_synthesis_prompt(query, obs, last_tool_name, chat_history=chat_history)
        print("++++++++++++++++++++++++++++++++++++++++++++++++")

        print("prompt + context + history: ", prompt)
        print("++++++++++++++++++++++++++++++++++++++++++++++++")
        stream_success = False
        try:
            async for chunk in self.llm.astream(prompt):
                token_text = self._extract_text(chunk.content)
                if token_text:
                    stream_success = True
                    yield {"type": "token", "content": token_text}
        except Exception:
            # Tự động chuyển đổi sang fallback_llm nếu mô hình chính bị quá tải 503
            if not stream_success:
                try:
                    async for chunk in self.fallback_llm.astream(prompt):
                        token_text = self._extract_text(chunk.content)
                        if token_text:
                            yield {"type": "token", "content": token_text}
                except Exception as fallback_err:
                    yield {"type": "token", "content": f"Lỗi trong quá trình sinh câu trả lời: {str(fallback_err)}"}
            else:
                yield {"type": "token", "content": "\n[Đã ngắt kết nối do mạng không ổn định]"}

        yield {"type": "done"}
