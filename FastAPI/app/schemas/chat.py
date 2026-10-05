from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


# 1. DTO tạo mới phiên hội thoại
class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field("Cuộc trò chuyện mới", max_length=255, description="Tiêu đề phiên chat")
    document_ids: Optional[list[UUID]] = Field(None, description="Danh sách tài liệu liên kết với phiên chat")


# 2. DTO cập nhật tiêu đề phiên chat
class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề mới cho phiên chat")


# 2.5 DTO tài liệu gắn kèm phiên chat
class SessionDocumentItem(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int

    model_config = ConfigDict(from_attributes=True)


# 3. DTO chi tiết phiên hội thoại
class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    document_id: Optional[UUID] = None
    documents: list[SessionDocumentItem] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 4. DTO gửi tin nhắn vào phiên chat
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Nội dung câu hỏi của người dùng")


# 5. DTO chi tiết một tin nhắn
class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: Optional[Any] = None
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 6. DTO phản hồi khi gửi tin nhắn (trả về cả tin nhắn user và câu trả lời AI)
class SendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


# 7. DTO phản hồi khi tạo phiên chat kèm tài liệu và câu hỏi
class SessionUploadAndChatResponse(BaseModel):
    session: ChatSessionResponse
    user_message: Optional[ChatMessageResponse] = None
    assistant_message: Optional[ChatMessageResponse] = None
    uploaded_documents: list[SessionDocumentItem] = []


# 8. DTO phản hồi khi nạp thêm tài liệu vào phiên chat hiện tại (kèm câu hỏi tùy chọn)
class AddDocumentsAndChatResponse(BaseModel):
    session_id: UUID
    user_message: Optional[ChatMessageResponse] = None
    assistant_message: Optional[ChatMessageResponse] = None
    newly_uploaded: list[SessionDocumentItem] = []
    all_session_documents: list[SessionDocumentItem] = []


# 9. DTO phản hồi khi xóa phiên chat
class DeleteSessionResponse(BaseModel):
    message: str = "Phiên trò chuyện đã được xóa thành công"
    id: UUID
