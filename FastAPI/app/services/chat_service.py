import uuid
import json
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.session_document import session_documents
from app.services.rag_service import RAGService
from app.core.repository import BaseRepository
from app.core.exceptions import (
    ChatSessionNotFoundException,
    EmptyMessageException,
)


class ChatService:
    """
    Tầng Service quản lý phiên trò chuyện và tương tác RAG:
    - Quản lý vòng đời ChatSession (Tạo, xem danh sách, cập nhật tên, xóa mềm) qua BaseRepository.
    - Quản lý liên kết nhiều tài liệu với từng ChatSession (session_documents).
    - Tải lịch sử tin nhắn ChatMessage.
    - Tương tác RAG: Truy xuất ngữ cảnh từ tất cả tài liệu trong phiên chat và sinh câu trả lời qua Google Gemini.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = BaseRepository(db, ChatSession)
        self.msg_repo = BaseRepository(db, ChatMessage)
        self.doc_repo = BaseRepository(db, Document)

    async def get_session_documents(self, session_id: uuid.UUID) -> list[Document]:
        """Lấy danh sách các tài liệu liên kết với một phiên chat."""
        session = await self.session_repo.find_by_id(session_id, include=[ChatSession.documents])
        if not session:
            return []
        return [d for d in session.documents if not d.is_deleted]

    async def link_documents_to_session(self, session_id: uuid.UUID, doc_ids: list[uuid.UUID]) -> None:
        """Gắn danh sách document_ids vào bảng liên kết session_documents."""
        unique_ids = list(dict.fromkeys(doc_ids))
        for d_id in unique_ids:
            stmt = (
                insert(session_documents)
                .values(session_id=session_id, document_id=d_id)
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)
        await self.db.flush()

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: Optional[str] = "Cuộc trò chuyện mới",
        document_ids: Optional[list[uuid.UUID]] = None,
    ) -> ChatSession:
        """Tạo một phiên hội thoại mới cho User."""
        primary_doc_id = document_ids[0] if document_ids else None
        session = await self.session_repo.create(
            title=title or "Cuộc trò chuyện mới",
            user_id=user_id,
            document_id=primary_doc_id,
        )

        if document_ids:
            await self.link_documents_to_session(session.id, document_ids)

        session.documents = await self.get_session_documents(session.id)
        return session

    async def get_sessions(self, user_id: uuid.UUID) -> list[ChatSession]:
        """Lấy danh sách các phiên chat của User (chưa bị xóa mềm)."""
        sessions = await self.session_repo.find_many(
            user_id=user_id,
            is_deleted=False,
            include=[ChatSession.documents],
            order_by=ChatSession.updated_at.desc()
        )
        for s in sessions:
            s.documents = [d for d in s.documents if not d.is_deleted]
        return sessions

    async def get_session_by_id(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> ChatSession:
        """Lấy thông tin chi tiết một phiên chat, kiểm tra quyền sở hữu."""
        session = await self.session_repo.find_one(
            id=session_id,
            user_id=user_id,
            is_deleted=False,
            include=[ChatSession.documents]
        )
        if not session:
            raise ChatSessionNotFoundException("Phiên trò chuyện không tồn tại hoặc bạn không có quyền truy cập")
        session.documents = [d for d in session.documents if not d.is_deleted]
        return session

    async def update_session_title(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str
    ) -> ChatSession:
        """Đổi tên tiêu đề của phiên chat."""
        session = await self.get_session_by_id(session_id, user_id)
        session = await self.session_repo.update(session.id, title=title.strip())
        session.documents = await self.get_session_documents(session.id)
        return session

    async def delete_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> ChatSession:
        """Xóa mềm phiên chat."""
        session = await self.get_session_by_id(session_id, user_id)
        await self.session_repo.delete(session.id, soft=True)
        return session

    async def get_session_messages(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> list[ChatMessage]:
        """Tải toàn bộ lịch sử tin nhắn trong phiên chat (sắp xếp tăng dần theo thời gian)."""
        await self.get_session_by_id(session_id, user_id)
        return await self.msg_repo.find_many(
            session_id=session_id,
            is_deleted=False,
            order_by=ChatMessage.created_at.asc()
        )

    async def _resolve_session_target_doc_ids(self, session: ChatSession) -> tuple[Optional[list[uuid.UUID]], list[Document]]:
        """
        Xác định danh sách document_ids mục tiêu cho phiên chat:
        - Nếu phiên chat có cấu hình tài liệu riêng: chỉ tìm kiếm trên các tài liệu còn tồn tại (chưa xóa mềm).
        - Nếu toàn bộ tài liệu cấu hình đã bị xóa mềm: trả về [] (không tìm kiếm).
        - Nếu phiên chat không gán tài liệu nào: trả về None (tìm kiếm toàn bộ kho tài liệu của user).
        """
        session_docs = await self.get_session_documents(session.id)
        doc_ids = [d.id for d in session_docs]

        if session.document_id and session.document_id not in doc_ids:
            primary_doc = await self.doc_repo.find_by_id(session.document_id)
            if primary_doc and not primary_doc.is_deleted:
                doc_ids.append(session.document_id)

        cfg_stmt = select(session_documents.c.document_id).where(session_documents.c.session_id == session.id)
        cfg_res = await self.db.execute(cfg_stmt)
        configured_doc_ids = [r[0] for r in cfg_res.all()]
        if session.document_id and session.document_id not in configured_doc_ids:
            configured_doc_ids.append(session.document_id)

        is_doc_specific = len(configured_doc_ids) > 0
        target_doc_ids = doc_ids if doc_ids else ([] if is_doc_specific else None)
        return target_doc_ids, session_docs

    @staticmethod
    def _truncate_title(text: str, max_len: int = 40) -> str:
        """Tạo tiêu đề ngắn gọn từ câu hỏi của người dùng."""
        cleaned = text.strip()
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[:max_len] + "..."

    async def _create_and_persist_assistant_message(
        self,
        session_id: uuid.UUID,
        rag_result,
    ) -> ChatMessage:
        """Tạo và lưu trữ phản hồi của AI Assistant vào Database."""
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=rag_result.answer,
            sources=rag_result.sources,
            model_name=rag_result.model_name,
            prompt_tokens=rag_result.prompt_tokens,
            completion_tokens=rag_result.completion_tokens,
            total_tokens=rag_result.total_tokens,
        )
        self.db.add(assistant_msg)
        return assistant_msg

    async def _prepare_chat_turn(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str
    ) -> tuple[ChatSession, ChatMessage, Optional[list[uuid.UUID]], list[dict], list[Document]]:
        """
        Hàm helper dùng chung cho cả send_message và send_message_stream:
        1. Kiểm tra tính hợp lệ của tin nhắn.
        2. Lưu tin nhắn của người dùng (user_msg) và cập nhật tiêu đề session nếu cần.
        3. Xác định danh sách document_ids liên quan đến phiên chat.
        4. Tải lịch sử tin nhắn gần nhất để làm ngữ cảnh đa lượt (Multi-turn Context).
        """
        clean_content = content.strip()
        if not clean_content:
            raise EmptyMessageException("Nội dung tin nhắn không được để trống")

        session = await self.get_session_by_id(session_id, user_id)

        # Lưu tin nhắn của người dùng
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=clean_content
        )
        self.db.add(user_msg)

        # Cập nhật tiêu đề nếu vẫn để mặc định
        if session.title == "Cuộc trò chuyện mới":
            session.title = self._truncate_title(clean_content)

        # Xác định tài liệu mục tiêu
        target_doc_ids, session_docs = await self._resolve_session_target_doc_ids(session)

        # Lấy 6 tin nhắn gần nhất (trừ tin nhắn hiện tại vừa gửi)
        recent_messages = await self.get_session_messages(session_id, user_id)
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in recent_messages if m.id != user_msg.id
        ][-6:]

        await self.db.commit()
        return session, user_msg, target_doc_ids, chat_history, session_docs

    async def send_message(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str
    ) -> tuple[ChatMessage, ChatMessage]:
        """
        Gửi câu hỏi vào phiên chat và kích hoạt RAG (chế độ Đồng bộ / JSON):
        1. Chuẩn bị ngữ cảnh qua _prepare_chat_turn.
        2. Kích hoạt RAGService.query để tìm kiếm và sinh câu trả lời.
        3. Lưu tin nhắn phản hồi của Assistant vào DB.
        """
        session, user_msg, target_doc_ids, chat_history, session_docs = await self._prepare_chat_turn(
            session_id=session_id,
            user_id=user_id,
            content=content
        )

        rag_service = RAGService(self.db)
        rag_result = await rag_service.query(
            query=user_msg.content,
            user_id=user_id,
            document_ids=target_doc_ids,
            chat_history=chat_history
        )

        assistant_msg = await self._create_and_persist_assistant_message(session_id, rag_result)

        await self.db.commit()
        await self.db.refresh(user_msg)
        await self.db.refresh(assistant_msg)
        await self.db.refresh(session)
        session.documents = session_docs

        return user_msg, assistant_msg

    async def upload_and_create_session(
        self,
        user_id: uuid.UUID,
        files: list,
        content: Optional[str] = None,
        title: Optional[str] = None
    ) -> tuple[ChatSession, Optional[ChatMessage], Optional[ChatMessage], list]:
        """
        Khởi tạo phiên trò chuyện mới kèm tải lên 1 hoặc nhiều tài liệu và câu hỏi tùy chọn:
        - Tải và xử lý RAG cho danh sách tài liệu.
        - Khởi tạo ChatSession và liên kết tài liệu vào session_documents.
        - Nếu có câu hỏi: Kích hoạt RAG trả lời ngay trên các tài liệu vừa tải lên.
        """
        from app.services.document_service import DocumentService

        doc_service = DocumentService(self.db)
        batch_result = await doc_service.upload_multiple_documents(files=files, user_id=user_id)
        uploaded_docs = batch_result.get("uploaded", [])

        clean_content = content.strip() if content else None

        session_title = title
        if not session_title:
            if clean_content:
                session_title = self._truncate_title(clean_content)
            elif uploaded_docs:
                session_title = f"Hỏi đáp: {uploaded_docs[0].filename}"
            else:
                session_title = "Cuộc trò chuyện mới"

        primary_doc_id = uploaded_docs[0].id if uploaded_docs else None
        session = ChatSession(
            title=session_title,
            user_id=user_id,
            document_id=primary_doc_id,
        )
        self.db.add(session)
        await self.db.flush()

        doc_ids = [d.id for d in uploaded_docs]
        if doc_ids:
            await self.link_documents_to_session(session.id, doc_ids)

        user_msg: Optional[ChatMessage] = None
        assistant_msg: Optional[ChatMessage] = None

        user_attached_sources = [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size": d.file_size
            }
            for d in uploaded_docs
        ] if uploaded_docs else None

        if clean_content or user_attached_sources:
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=clean_content or "",
                sources=user_attached_sources
            )
            self.db.add(user_msg)

            if clean_content:
                rag_service = RAGService(self.db)
                rag_result = await rag_service.query(
                    query=clean_content,
                    user_id=user_id,
                    document_ids=doc_ids if doc_ids else None
                )
                assistant_msg = await self._create_and_persist_assistant_message(session.id, rag_result)

        await self.db.commit()
        await self.db.refresh(session)
        session.documents = await self.get_session_documents(session.id)
        if user_msg:
            await self.db.refresh(user_msg)
        if assistant_msg:
            await self.db.refresh(assistant_msg)

        return session, user_msg, assistant_msg, uploaded_docs

    async def upload_to_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        files: list,
        content: Optional[str] = None
    ) -> tuple[ChatSession, Optional[ChatMessage], Optional[ChatMessage], list, list]:
        """
        Tải thêm 1 hoặc nhiều tài liệu vào phiên trò chuyện hiện tại (kèm câu hỏi tùy chọn):
        - Tải và xử lý RAG cho các tài liệu mới.
        - Gắn thêm các tài liệu mới vào session_documents.
        - Nếu có câu hỏi: RAG sẽ truy xuất trên TẤT CẢ tài liệu của session (cả cũ và mới).
        """
        from app.services.document_service import DocumentService

        session = await self.get_session_by_id(session_id, user_id)

        doc_service = DocumentService(self.db)
        batch_result = await doc_service.upload_multiple_documents(files=files, user_id=user_id)
        newly_uploaded = batch_result.get("uploaded", [])

        new_doc_ids = [d.id for d in newly_uploaded]
        if new_doc_ids:
            await self.link_documents_to_session(session.id, new_doc_ids)

        all_session_docs = await self.get_session_documents(session.id)
        all_doc_ids = [d.id for d in all_session_docs]

        user_msg: Optional[ChatMessage] = None
        assistant_msg: Optional[ChatMessage] = None

        clean_content = content.strip() if content else None
        user_attached_sources = [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "file_size": d.file_size
            }
            for d in newly_uploaded
        ] if newly_uploaded else None

        if clean_content or user_attached_sources:
            user_msg = ChatMessage(
                session_id=session.id,
                role="user",
                content=clean_content or "",
                sources=user_attached_sources
            )
            self.db.add(user_msg)

            if clean_content:
                recent_messages = await self.get_session_messages(session.id, user_id)
                chat_history = [
                    {"role": m.role, "content": m.content}
                    for m in recent_messages if m.id != user_msg.id
                ][-6:]

                rag_service = RAGService(self.db)
                rag_result = await rag_service.query(
                    query=clean_content,
                    user_id=user_id,
                    document_ids=all_doc_ids if all_doc_ids else None,
                    chat_history=chat_history
                )
                assistant_msg = await self._create_and_persist_assistant_message(session.id, rag_result)

        await self.db.commit()
        await self.db.refresh(session)
        session.documents = all_session_docs
        if user_msg:
            await self.db.refresh(user_msg)
        if assistant_msg:
            await self.db.refresh(assistant_msg)

        return session, user_msg, assistant_msg, newly_uploaded, all_session_docs

    async def send_message_stream(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str
    ):
        """
        Gửi câu hỏi và stream phản hồi từ AI về Client qua SSE:
        1. Chuẩn bị ngữ cảnh qua _prepare_chat_turn.
        2. Kích hoạt luồng Stream từ RAGService và đẩy từng event về Client.
        3. Bắt lỗi ngoại lệ và gửi event lỗi nếu có.
        4. Lưu câu trả lời hoàn chỉnh của Assistant và trích dẫn vào PostgreSQL khi stream kết thúc.
        """
        session, user_msg, target_doc_ids, chat_history, _ = await self._prepare_chat_turn(
            session_id=session_id,
            user_id=user_id,
            content=content
        )

        rag_service = RAGService(self.db)
        full_tokens = []
        collected_sources = []

        try:
            async for event_obj in rag_service.stream_query(
                query=user_msg.content,
                user_id=user_id,
                document_ids=target_doc_ids,
                chat_history=chat_history
            ):
                event_type = event_obj.get("type")

                if event_type == "sources":
                    collected_sources = event_obj.get("data", [])
                    yield f"event: sources\ndata: {json.dumps(collected_sources)}\n\n"

                elif event_type == "token":
                    token_text = event_obj.get("content", "")
                    full_tokens.append(token_text)
                    yield f"event: token\ndata: {json.dumps({'text': token_text})}\n\n"
                    
                elif event_type == "done":
                    yield f"event: done\ndata: [DONE]\n\n"
        except Exception as e:
            error_msg = f"Đã xảy ra lỗi trong quá trình xử lý: {str(e)}"
            yield f"event: token\ndata: {json.dumps({'text': error_msg})}\n\n"
            yield f"event: done\ndata: [DONE]\n\n"
            full_tokens.append(error_msg)

        # Lưu câu trả lời hoàn chỉnh của AI vào DB độc lập (AsyncSessionLocal)
        full_answer = "".join(full_tokens).strip()
        if full_answer:
            try:
                async with AsyncSessionLocal() as persist_db:
                    assistant_msg = ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=full_answer,
                        sources=collected_sources if collected_sources else None,
                        model_name=settings.LLM_MODEL,
                    )
                    persist_db.add(assistant_msg)
                    await persist_db.commit()
            except Exception as e:
                print(f"[ChatService] Error: Failed to persist streamed assistant message: {e}")
