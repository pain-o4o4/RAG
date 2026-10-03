from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime


# 1. DTO nhận dữ liệu khi Đăng ký
class RegisterRequest(BaseModel):
    user_name: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập (3-50 ký tự)")
    email: EmailStr = Field(..., description="Địa chỉ email hợp lệ")
    password: str = Field(..., min_length=6, max_length=100, description="Mật khẩu (ít nhất 6 ký tự)")


# 2. DTO nhận dữ liệu khi Đăng nhập
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email đăng nhập")
    password: str = Field(..., description="Mật khẩu")


# 3. DTO trả về thông tin User (ẩn hoàn toàn mật khẩu)
class UserResponse(BaseModel):
    id: UUID
    user_name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 4. DTO phản hồi khi Đăng nhập thành công (khi chưa dùng JWT)
class LoginResponse(BaseModel):
    message: str = "Đăng nhập thành công"
    user: UserResponse
