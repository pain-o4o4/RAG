from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


# 1. DTO chi tiết một tài liệu
class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_size: int
    file_type: str
    file_hash: Optional[str] = None
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 2. DTO danh sách tài liệu có phân trang
class DocumentPaginationResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# 3. DTO phản hồi khi xóa tài liệu
class DeleteDocumentResponse(BaseModel):
    message: str = "Tài liệu đã được xóa thành công"
    id: UUID


# 4. DTO thông tin file tải lên thất bại
class FailedUploadItem(BaseModel):
    filename: str
    reason: str


# 5. DTO phản hồi khi tải lên 1 hoặc nhiều tài liệu (Batch Upload)
class BatchUploadResponse(BaseModel):
    total_uploaded: int
    total_failed: int
    uploaded: list[DocumentResponse]
    failed: list[FailedUploadItem]

