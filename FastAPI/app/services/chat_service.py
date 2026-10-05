import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.core.config import settings

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

    async def send_message(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str
    ) -> tuple[ChatMessage, ChatMessage]:
        """
        Gửi câu hỏi vào phiên chat và kích hoạt RAG:
        1. Tìm kiếm context trên TẤT CẢ tài liệu đã gắn với phiên chat này.
        2. Nếu phiên chat chưa có tài liệu gắn riêng, tìm kiếm trên kho tài liệu của user.
        3. Gọi Google Gemini API để sinh câu trả lời kèm trích dẫn (sources).
        """
        clean_content = content.strip()
        if not clean_content:
            raise EmptyMessageException("Nội dung tin nhắn không được để trống")

        session = await self.get_session_by_id(session_id, user_id)

        # 1. Lưu tin nhắn của người dùng
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=clean_content
        )
        self.db.add(user_msg)

        # 2. Cập nhật tiêu đề nếu vẫn để mặc định
        if session.title == "Cuộc trò chuyện mới":
            session.title = clean_content[:40] + ("..." if len(clean_content) > 40 else "")

        # 3. Lấy tất cả document_ids thuộc phiên chat
        session_docs = await self.get_session_documents(session_id)
        doc_ids = [d.id for d in session_docs]
        if session.document_id and session.document_id not in doc_ids:
            doc_ids.append(session.document_id)

        # 4. Kích hoạt RAG Service riêng biệt
        recent_messages = await self.get_session_messages(session_id, user_id)
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in recent_messages if m.id != user_msg.id
        ][-6:]

        rag_service = RAGService(self.db)
        rag_result = await rag_service.query(
            query=clean_content,
            user_id=user_id,
            document_ids=doc_ids if doc_ids else None,
            chat_history=chat_history
        )

        # 5. Lưu tin nhắn phản hồi của Assistant
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

        # Xác định tiêu đề mặc định
        session_title = title
        if not session_title:
            if content and content.strip():
                session_title = content.strip()[:40] + ("..." if len(content.strip()) > 40 else "")
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

        # Liên kết tất cả tài liệu vào session_documents
        doc_ids = [d.id for d in uploaded_docs]
        if doc_ids:
            await self.link_documents_to_session(session.id, doc_ids)

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

            rag_service = RAGService(self.db)
            rag_result = await rag_service.query(
                query=clean_content,
                user_id=user_id,
                document_ids=doc_ids if doc_ids else None
            )

            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=rag_result.answer,
                sources=rag_result.sources,
                model_name=rag_result.model_name,
                prompt_tokens=rag_result.prompt_tokens,
                completion_tokens=rag_result.completion_tokens,
                total_tokens=rag_result.total_tokens,
            )
            self.db.add(assistant_msg)

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

        # Thêm các tài liệu mới vào session_documents
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

            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=rag_result.answer,
                sources=rag_result.sources,
                model_name=rag_result.model_name,
                prompt_tokens=rag_result.prompt_tokens,
                completion_tokens=rag_result.completion_tokens,
                total_tokens=rag_result.total_tokens,
            )
            self.db.add(assistant_msg)

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
        Gửi câu hỏi và sinh phản hồi dạng Streaming qua Server-Sent Events (SSE):
        - 1. Lưu câu hỏi của User vào cơ sở dữ liệu.
        - 2. Kích hoạt luồng Stream từ RAGService và đẩy từng event về Client.
        - 3. Lưu câu trả lời hoàn chỉnh của Assistant và trích dẫn vào PostgreSQL khi stream kết thúc.
        """
        import json
        clean_content = content.strip()
        if not clean_content:
            raise EmptyMessageException("Nội dung tin nhắn không được để trống")

        session = await self.get_session_by_id(session_id, user_id)

        # 1. Lưu tin nhắn người dùng
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=clean_content
        )
        self.db.add(user_msg)
        if session.title == "Cuộc trò chuyện mới":
            session.title = clean_content[:40] + ("..." if len(clean_content) > 40 else "")

        session_docs = await self.get_session_documents(session_id)
        doc_ids = [d.id for d in session_docs]
        if session.document_id and session.document_id not in doc_ids:
            doc_ids.append(session.document_id)

        recent_messages = await self.get_session_messages(session_id, user_id)
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in recent_messages if m.id != user_msg.id
        ][-6:]

        await self.db.commit()

        # 2. Khởi chạy luồng RAG Stream
        rag_service = RAGService(self.db)
        full_tokens = []
        collected_sources = []

        async for sse_event in rag_service.stream_query(
            query=clean_content,
            user_id=user_id,
            document_ids=doc_ids if doc_ids else None,
            chat_history=chat_history
        ):
            yield sse_event

            # Bóc tách dữ liệu để chuẩn bị lưu trữ vào DB
            for line in sse_event.strip().split("\n"):
                if line.startswith("data:"):
                    raw_data = line[5:].strip()
                    if raw_data == "[DONE]":
                        continue
                    try:
                        parsed = json.loads(raw_data)
                        if isinstance(parsed, list):
                            collected_sources = parsed
                        elif isinstance(parsed, dict) and "text" in parsed:
                            full_tokens.append(parsed["text"])
                    except Exception:
                        pass

        # 3. Lưu câu trả lời hoàn chỉnh của AI vào DB
        full_answer = "".join(full_tokens).strip()
        if full_answer:
            try:
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=full_answer,
                    sources=collected_sources,
                    model_name=settings.LLM_MODEL,
                )
                self.db.add(assistant_msg)
                await self.db.commit()
            except Exception as e:
                print(f"[ChatService] Warning: Failed to persist streamed assistant message: {e}")
