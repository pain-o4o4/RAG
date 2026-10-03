from collections.abc import AsyncGenerator
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User


async def get_current_user(
    x_user_id: Optional[str] = Header(
        None, 
        alias="X-User-Id", 
        description="ID người dùng giả lập (UUID) khi chưa dùng JWT"
    ),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency trích xuất thông tin người dùng đang thao tác:
    - Nếu Client truyền Header 'X-User-Id': Xác thực theo đúng User đó.
    - Nếu Client không truyền: Tự động lấy User active gần nhất trong DB (hỗ trợ test Swagger nhanh chóng).
    - Sau này khi nâng cấp JWT (Refresh Token), chỉ cần thay đổi nội dung hàm này mà KHÔNG cần sửa bất kỳ Router nào!
    """
    if x_user_id:
        try:
            user_uuid = UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Header X-User-Id không đúng định dạng UUID"
            )
        query = select(User).where(User.id == user_uuid, User.is_deleted == False)
        result = await db.execute(query)
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Người dùng gắn với X-User-Id không tồn tại"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản này đã bị khóa"
            )
        return user

    # Fallback cho môi trường dev khi chưa gắn JWT
    query = (
        select(User)
        .where(User.is_active == True, User.is_deleted == False)
        .order_by(User.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hệ thống chưa có người dùng nào. Vui lòng đăng ký tài khoản trước."
        )
    return user


__all__ = [
    "get_db",
    "get_current_user",
]
