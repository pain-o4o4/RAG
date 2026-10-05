from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.chat import (
    CreateSessionRequest,
    UpdateSessionRequest,
    ChatSessionResponse,
    SendMessageRequest,
    ChatMessageResponse,
    SendMessageResponse,
    DeleteSessionResponse,
    SessionUploadAndChatResponse,
    AddDocumentsAndChatResponse,
    SessionDocumentItem,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat & RAG Interaction"])


# ============================================================================
# 1. QUẢN LÝ PHIÊN HỘI THOẠI (CHAT SESSIONS)
# ============================================================================

@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mới một phiên trò chuyện"
)
async def create_session(
    payload: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tạo mới một phiên trò chuyện:
    - Có thể đặt tiêu đề tùy chọn hoặc để mặc định.
    - Có thể truyền document_id nếu muốn trò chuyện về 1 tài liệu cụ thể.
    """
    service = ChatService(db)
    session = await service.create_session(
        user_id=current_user.id,
        title=payload.title,
        document_ids=payload.document_ids,
    )
    return session


@router.post(
    "/sessions/upload",
    response_model=SessionUploadAndChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phiên hội thoại mới kèm tải lên 1 hoặc nhiều tài liệu và câu hỏi tùy chọn"
)
async def create_session_with_upload(
    files: list[UploadFile] = File(..., description="Danh sách các file tài liệu (PDF, DOCX, TXT)"),
    content: Optional[str] = Form(None, description="Câu hỏi hoặc prompt đầu tiên (tùy chọn)"),
    title: Optional[str] = Form(None, description="Tiêu đề phiên chat tùy chọn"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trải nghiệm kéo thả file & hỏi đáp tức thì (tương tự giao diện web ChatGPT / Gemini):
    - Tải lên 1 hoặc nhiều file cùng lúc (PDF, DOCX, TXT).
    - Có thể gửi kèm câu hỏi/prompt ngay trong cùng request.
    - Hệ thống xử lý RAG tức thì trên các file vừa tải và trả lời kèm trích dẫn nguồn.
    - Tạo mới một session_id để người dùng có thể tiếp tục hỏi thêm sau đó.
    """
    service = ChatService(db)
    session, user_msg, assistant_msg, uploaded_docs = await service.upload_and_create_session(
        user_id=current_user.id,
        files=files,
        content=content,
        title=title,
    )
    return SessionUploadAndChatResponse(
        session=ChatSessionResponse.model_validate(session),
        user_message=ChatMessageResponse.model_validate(user_msg) if user_msg else None,
        assistant_message=ChatMessageResponse.model_validate(assistant_msg) if assistant_msg else None,
        uploaded_documents=[SessionDocumentItem.model_validate(d) for d in uploaded_docs],
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách các phiên trò chuyện của người dùng"
)
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách tất cả các cuộc hội thoại chưa bị xóa của User."""
    service = ChatService(db)
    sessions = await service.get_sessions(user_id=current_user.id)
    return sessions


@router.get(
    "/sessions/{id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy chi tiết một phiên trò chuyện"
)
async def get_session(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xem thông tin chi tiết phiên chat."""
    service = ChatService(db)
    session = await service.get_session_by_id(session_id=id, user_id=current_user.id)
    return session


@router.patch(
    "/sessions/{id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật tiêu đề phiên trò chuyện"
)
async def update_session_title(
    id: UUID,
    payload: UpdateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Đổi tên tiêu đề của phiên chat."""
    service = ChatService(db)
    session = await service.update_session_title(
        session_id=id,
        user_id=current_user.id,
        title=payload.title,
    )
    return session


@router.delete(
    "/sessions/{id}",
    response_model=DeleteSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Xóa một phiên trò chuyện"
)
async def delete_session(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Xóa mềm phiên trò chuyện."""
    service = ChatService(db)
    session = await service.delete_session(session_id=id, user_id=current_user.id)
    return DeleteSessionResponse(
        message="Phiên trò chuyện đã được xóa thành công",
        id=session.id,
    )


# ============================================================================
# 2. TIN NHẮN & TƯƠNG TÁC RAG (CHAT MESSAGES & RAG INTERACTION)
# ============================================================================

@router.get(
    "/sessions/{id}/messages",
    response_model=list[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Tải toàn bộ lịch sử tin nhắn trong phiên"
)
async def get_messages(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy toàn bộ lịch sử tin nhắn của phiên chat theo thứ tự thời gian.
    - Kiểm tra quyền sở hữu của User với phiên chat này.
    - Trả về 404 nếu không tìm thấy phiên chat.
    """
    service = ChatService(db)
    messages = await service.get_session_messages(session_id=id, user_id=current_user.id)
    return messages


@router.post(
    "/sessions/{id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi câu hỏi, kích hoạt RAG tìm kiếm và sinh câu trả lời"
)
async def send_message(
    id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Gửi câu hỏi và nhận câu trả lời từ AI:
    - 1. Tiếp nhận payload câu hỏi từ Client.
    - 2. Chuyển giao sang ChatService để:
         + Lưu tin nhắn User.
         + Tự động trích xuất các đoạn DocumentChunk liên quan (Retrieval).
         + Gọi mô hình Google Gemini để sinh phản hồi (Generation).
         + Lưu tin nhắn Assistant kèm trích dẫn sources.
    - 3. Trả về cả tin nhắn của User và tin phản hồi của Assistant.
    """
    service = ChatService(db)
    user_msg, assistant_msg = await service.send_message(
        session_id=id,
        user_id=current_user.id,
        content=payload.content,
    )
    return SendMessageResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
    )


@router.post(
    "/sessions/{id}/upload",
    response_model=AddDocumentsAndChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Tải thêm tài liệu vào phiên trò chuyện hiện tại (kèm câu hỏi tùy chọn)"
)
async def upload_more_to_session(
    id: UUID,
    files: list[UploadFile] = File(..., description="Danh sách file tài liệu cần nạp thêm vào phiên chat"),
    content: Optional[str] = Form(None, description="Câu hỏi hoặc yêu cầu mới trên tất cả tài liệu (tùy chọn)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Nạp thêm tài liệu vào phiên trò chuyện đang diễn ra:
    - Bổ sung tài liệu vào ngữ cảnh của phiên chat này.
    - Nếu có câu hỏi kèm theo: RAG sẽ truy xuất trên TOÀN BỘ tài liệu của phiên chat (bao gồm cả tài liệu trước và tài liệu mới nạp).
    - Sau đó, người dùng hoàn toàn có thể tiếp tục gửi tin nhắn text thông thường qua POST /sessions/{id}/messages.
    """
    service = ChatService(db)
    session, user_msg, assistant_msg, newly_uploaded, all_session_docs = await service.upload_to_session(
        session_id=id,
        user_id=current_user.id,
        files=files,
        content=content,
    )
    return AddDocumentsAndChatResponse(
        session_id=session.id,
        user_message=ChatMessageResponse.model_validate(user_msg) if user_msg else None,
        assistant_message=ChatMessageResponse.model_validate(assistant_msg) if assistant_msg else None,
        newly_uploaded=[SessionDocumentItem.model_validate(d) for d in newly_uploaded],
        all_session_documents=[SessionDocumentItem.model_validate(d) for d in all_session_docs],
    )

