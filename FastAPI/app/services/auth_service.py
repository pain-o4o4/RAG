from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import get_password_hash, verify_password
from app.core.repository import BaseRepository
from app.core.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    InactiveUserException,
    AppException
)


class AuthService:
    """
    Tầng Service xác thực người dùng:
    - Sử dụng BaseRepository để truy vấn và lưu trữ (find_one, create) giống như Express / Mongoose.
    - Xử lý mã hóa mật khẩu bcrypt và kiểm tra trạng thái tài khoản.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = BaseRepository(db, User)

    async def register(self, payload: RegisterRequest) -> User:
        """
        Nghiệp vụ đăng ký tài khoản:
        1. Kiểm tra email hoặc user_name đã tồn tại chưa.
        2. Băm mật khẩu (bcrypt).
        3. Lưu User mới vào Database.
        """
        try:
            # 1. Kiểm tra trùng lặp
            existing_email = await self.user_repo.find_one(email=payload.email)
            if existing_email:
                raise UserAlreadyExistsException("Email này đã được sử dụng")

            existing_username = await self.user_repo.find_one(user_name=payload.user_name)
            if existing_username:
                raise UserAlreadyExistsException("Tên đăng nhập này đã được sử dụng")

            # 2. Tạo đối tượng User với mật khẩu đã băm
            new_user = await self.user_repo.create(
                user_name=payload.user_name,
                email=payload.email,
                hashed_password=get_password_hash(payload.password),
                is_active=True
            )
            return new_user
            
        except UserAlreadyExistsException:
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise AppException(status_code=500, detail=f"Lỗi cơ sở dữ liệu trong quá trình đăng ký: {str(e)}")
        except Exception as e:
            await self.db.rollback()
            raise AppException(status_code=500, detail=f"Lỗi hệ thống không xác định: {str(e)}")

    async def login(self, payload: LoginRequest) -> User:
        """
        Nghiệp vụ xác thực đăng nhập:
        1. Tìm kiếm User theo email (chưa bị xóa mềm).
        2. Kiểm tra mật khẩu băm.
        3. Kiểm tra trạng thái hoạt động (is_active).
        """
        try:
            # 1. Tìm user
            user = await self.user_repo.find_one(email=payload.email, is_deleted=False)

            # 2. So khớp mật khẩu
            if not user or not verify_password(payload.password, user.hashed_password):
                raise InvalidCredentialsException("Email hoặc mật khẩu không chính xác")

            # 3. Kiểm tra trạng thái khóa tài khoản
            if not user.is_active:
                raise InactiveUserException("Tài khoản của bạn đã bị khóa")

            return user
            
        except (InvalidCredentialsException, InactiveUserException):
            raise
        except SQLAlchemyError as e:
            raise AppException(status_code=500, detail=f"Lỗi cơ sở dữ liệu khi đăng nhập: {str(e)}")
        except Exception as e:
            raise AppException(status_code=500, detail=f"Lỗi hệ thống không xác định khi đăng nhập: {str(e)}")
