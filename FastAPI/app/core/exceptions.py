from fastapi import HTTPException, status


class AppException(HTTPException):
    """Lớp Exception cơ sở của toàn bộ dự án."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class UserAlreadyExistsException(AppException):
    def __init__(self, detail: str = "Email hoặc tên người dùng đã tồn tại"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InvalidCredentialsException(AppException):
    def __init__(self, detail: str = "Tài khoản hoặc mật khẩu không chính xác"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class InactiveUserException(AppException):
    def __init__(self, detail: str = "Tài khoản của bạn đã bị vô hiệu hóa"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UserNotFoundException(AppException):
    def __init__(self, detail: str = "Người dùng không tồn tại"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class DocumentNotFoundException(AppException):
    def __init__(self, detail: str = "Không tìm thấy tài liệu yêu cầu"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InvalidFileException(AppException):
    def __init__(self, detail: str = "Định dạng hoặc kích thước tệp tin không hợp lệ"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class DocumentAlreadyExistsException(AppException):
    def __init__(self, detail: str = "Tài liệu này đã tồn tại trong hệ thống"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ChatSessionNotFoundException(AppException):
    def __init__(self, detail: str = "Không tìm thấy phiên trò chuyện yêu cầu"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class EmptyMessageException(AppException):
    def __init__(self, detail: str = "Nội dung tin nhắn không được để trống"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


