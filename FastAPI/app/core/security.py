import bcrypt


def get_password_hash(password: str) -> str:
    """
    Băm mật khẩu plain-text sang chuỗi bcrypt an toàn.
    Sử dụng trực tiếp thư viện bcrypt native để tránh lỗi xung đột phiên bản của passlib.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Kiểm tra mật khẩu người dùng nhập vào có khớp với mật khẩu đã hash trong DB không.
    """
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)
