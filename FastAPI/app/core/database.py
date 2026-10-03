from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from sqlalchemy.orm import declarative_base

# tao quan ly ket noi voi db su dung bat dong bo async
engine = create_async_engine(settings.DATABASE_URL, echo=False)
# tao bo may tao ket noi voi db (tao session)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, # Tham chieu den engine
    class_=AsyncSession, # Tham chieu den AsyncSession
    expire_on_commit=False # KHÔNG xóa dữ liệu trên RAM sau khi commit, ngăn lỗi truy vấn ngầm 
)
Base = declarative_base()


async def get_db() -> AsyncSession:
    # async with sẽ tự động bao bọc try..except..finally và close() ở bên dưới
    async with AsyncSessionLocal() as session:
        yield session