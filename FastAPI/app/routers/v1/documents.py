import math
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentPaginationResponse,
    DeleteDocumentResponse,
    BatchUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Document Management"])


@router.post(
    "/upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên một hoặc nhiều tài liệu (.pdf, .docx, .txt)"
)
async def upload_documents(
    files: list[UploadFile] = File(..., description="Danh sách một hoặc nhiều tệp tin cần tải lên"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tiếp nhận một hoặc nhiều tệp tin từ Client:
    - 1. Chuyển giao sang DocumentService để xử lý batch upload kiên cường (resilient).
    - 2. Tự động lọc các file hợp lệ để lưu trữ và tạo bản ghi PENDING.
    - 3. Ghi nhận các file lỗi (sai định dạng, trùng lặp) vào danh sách failed.
    - 4. Trả về kết quả tổng hợp BatchUploadResponse.
    """
    service = DocumentService(db)
    result = await service.upload_multiple_documents(files=files, user_id=current_user.id)
    return result


@router.get(
    "",
    response_model=DocumentPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách tài liệu của người dùng (có phân trang)"
)
async def get_documents(
    page: int = Query(1, ge=1, description="Số thứ tự trang (bắt đầu từ 1)"),
    limit: int = Query(10, ge=1, le=100, description="Số bản ghi trên mỗi trang"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: PENDING, PROCESSING, COMPLETED, FAILED"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên tệp tin"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lấy danh sách tài liệu thuộc quyền sở hữu của User:
    - Có hỗ trợ phân trang (page, limit).
    - Có hỗ trợ tìm kiếm theo tên và lọc theo trạng thái xử lý.
    """
    service = DocumentService(db)
    items, total = await service.get_documents(
        user_id=current_user.id,
        page=page,
        limit=limit,
        status=status,
        search=search,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 0

    return DocumentPaginationResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get(
    "/{doc_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết 1 tài liệu và trạng thái xử lý"
)
async def get_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Xem thông tin chi tiết một tài liệu:
    - Kiểm tra quyền sở hữu của user đối với tài liệu này.
    - Trả về 404 nếu không tìm thấy hoặc đã bị xóa.
    """
    service = DocumentService(db)
    doc = await service.get_document_by_id(doc_id=doc_id, user_id=current_user.id)
    return doc


@router.delete(
    "/{doc_id}",
    response_model=DeleteDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Xóa mềm tài liệu"
)
async def delete_document(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Thực hiện xóa mềm (Soft Delete) tài liệu:
    - Chuyển cờ is_deleted = True và ghi nhận thời điểm xóa deleted_at.
    """
    service = DocumentService(db)
    doc = await service.delete_document(doc_id=doc_id, user_id=current_user.id)
    return DeleteDocumentResponse(
        message="Tài liệu đã được xóa thành công",
        id=doc.id,
    )
