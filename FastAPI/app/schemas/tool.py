from pydantic import BaseModel, Field
from typing import Optional


class KnowledgeSearchInput(BaseModel):
    """Schema tham số đầu vào cho công cụ tra cứu kho tài liệu nội bộ."""
    query: str = Field(
        ...,
        description="Từ khóa hoặc câu hỏi ngữ nghĩa ngắn gọn cần tìm kiếm trong tài liệu đã tải lên."
    )
    document_ids: Optional[list[str]] = Field(
        default=None,
        description="Danh sách ID tài liệu cần giới hạn phạm vi tìm kiếm (nếu có)."
    )


class ListUserDocumentsInput(BaseModel):
    """Schema tham số đầu vào cho công cụ xem danh sách tài liệu của người dùng."""
    keyword: Optional[str] = Field(
        default=None,
        description="Từ khóa lọc tên tài liệu nếu người dùng muốn tìm kiếm theo tên file cụ thể."
    )


class WebSearchInput(BaseModel):
    """Schema tham số đầu vào cho công cụ tìm kiếm thông tin trên Internet."""
    query: str = Field(
        ...,
        description="Câu truy vấn tìm kiếm thông tin trên Internet ngắn gọn và trọng tâm."
    )
