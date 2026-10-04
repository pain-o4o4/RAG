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
        description="ID người dùng (UUID)"
    ),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency trích xuất và xác thực người dùng từ Header X-User-Id:
    - Nếu có X-User-Id hợp lệ: Xác thực đúng tài khoản tương ứng.
    - Nếu chưa có hoặc X-User-Id không hợp lệ: Tự động fallback về tài khoản hoạt động trong DB
      để trải nghiệm giao diện Frontend và Swagger UI hoạt động liền mạch không bị chặn 401.
    """
    user = None
    if x_user_id and str(x_user_id).strip().lower() not in {"null", "undefined", "none", ""}:
        try:
            user_uuid = UUID(str(x_user_id).strip())
            query = select(User).where(User.id == user_uuid, User.is_deleted == False)
            result = await db.execute(query)
            user = result.scalars().first()
        except (ValueError, TypeError):
            user = None

    if not user:
        # Fallback về user đang hoạt động gần nhất trong DB
        fallback_query = (
            select(User)
            .where(User.is_deleted == False, User.is_active == True)
            .order_by(User.created_at.desc())
        )
        res = await db.execute(fallback_query)
        user = res.scalars().first()


    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa có tài khoản nào trong hệ thống. Vui lòng đăng nhập lại."
        )

    return user


__all__ = [
    "get_db",
    "get_current_user",
]
