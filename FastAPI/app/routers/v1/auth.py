from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    LoginResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới"
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Tiếp nhận yêu cầu đăng ký từ Client:
    - 1. Nhận dữ liệu đầu vào đã qua validate tự động bởi Pydantic.
    - 2. Điều hướng sang AuthService để xử lý nghiệp vụ băm pass và lưu DB.
    - 3. Trả về kết quả UserResponse (HTTP 201 Created).
    """
    auth_service = AuthService(db)
    user = await auth_service.register(payload)
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Đăng nhập xác thực tài khoản"
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Tiếp nhận yêu cầu đăng nhập từ Client:
    - 1. Nhận email và password.
    - 2. Điều hướng sang AuthService để kiểm tra mật khẩu và trạng thái tài khoản.
    - 3. Trả về thông báo thành công cùng thông tin User (HTTP 200 OK).
    """
    auth_service = AuthService(db)
    user = await auth_service.login(payload)
    return LoginResponse(
        message="Đăng nhập thành công",
        user=UserResponse.model_validate(user)
    )
