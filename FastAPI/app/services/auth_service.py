from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    InactiveUserException
)


class AuthService:
    """
    Tầng Service: Chịu trách nhiệm 100% về mặt nghiệp vụ logic và thao tác với Database.
    Tuyệt đối không để Router tự ý query hay commit Database.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: RegisterRequest) -> User:
        """
        Nghiệp vụ đăng ký tài khoản:
        1. Kiểm tra email hoặc user_name đã tồn tại chưa.
        2. Băm mật khẩu (bcrypt).
        3. Lưu User mới vào Database.
        """
        # 1. Kiểm tra trùng lặp
        query = select(User).where(
            or_(User.email == payload.email, User.user_name == payload.user_name)
        )
        result = await self.db.execute(query)
        existing_user = result.scalars().first()

        if existing_user:
            if existing_user.email == payload.email:
                raise UserAlreadyExistsException("Email này đã được sử dụng")
            raise UserAlreadyExistsException("Tên đăng nhập này đã được sử dụng")

        # 2. Tạo đối tượng User với mật khẩu đã băm
        new_user = User(
            user_name=payload.user_name,
            email=payload.email,
            hashed_password=get_password_hash(payload.password),
            is_active=True
        )

        # 3. Ghi vào DB
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user

    async def login(self, payload: LoginRequest) -> User:
        """
        Nghiệp vụ xác thực đăng nhập:
        1. Tìm kiếm User theo email (chưa bị xóa mềm).
        2. Kiểm tra mật khẩu băm.
        3. Kiểm tra trạng thái hoạt động (is_active).
        """
        # 1. Tìm user
        query = select(User).where(User.email == payload.email, User.is_deleted == False)
        result = await self.db.execute(query)
        user = result.scalars().first()

        # 2. So khớp mật khẩu
        if not user or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsException("Email hoặc mật khẩu không chính xác")

        # 3. Kiểm tra trạng thái khóa tài khoản
        if not user.is_active:
            raise InactiveUserException("Tài khoản của bạn đã bị khóa")

        return user
