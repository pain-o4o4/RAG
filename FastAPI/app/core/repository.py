import uuid
from typing import TypeVar, Generic, Type, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic Repository Pattern cho SQLAlchemy 2.0 Async:
    - Cung cấp giao diện tương tự Prisma / Sequelize / Mongoose (find_one, find_many, find_by_id, create, update, delete).
    - Hỗ trợ tham chiếu quan hệ khóa ngoại (Eager Loading / Populate / Include).
    - Hỗ trợ lọc (filter), sắp xếp (order_by), phân trang (limit, offset).
    - Hỗ trợ xóa mềm tự động (nếu Model có trường is_deleted).
    """

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    def _apply_options(self, stmt, include: Optional[list] = None):
        """Áp dụng nạp dữ liệu quan hệ khóa ngoại (tương tự include trong Prisma/Sequelize hoặc populate trong Mongoose)."""
        if include:
            for rel in include:
                stmt = stmt.options(selectinload(rel))
        return stmt

    async def find_by_id(self, id: Any, include: Optional[list] = None) -> Optional[T]:
        """
        Tìm 1 bản ghi theo Primary Key (ID).
        Tương đương: findByPk(id) hoặc findUnique({ where: { id } }).
        """
        if include:
            stmt = select(self.model).where(self.model.id == id)
            stmt = self._apply_options(stmt, include)
            res = await self.db.execute(stmt)
            return res.scalars().first()
        return await self.db.get(self.model, id)

    async def find_one(
        self,
        include: Optional[list] = None,
        order_by: Optional[Any] = None,
        **filters
    ) -> Optional[T]:
        """
        Tìm bản ghi đầu tiên khớp với bộ lọc.
        Tương đương: findOne({ where: { ... } }).
        """
        stmt = select(self.model).filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = self._apply_options(stmt, include)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def find_many(
        self,
        include: Optional[list] = None,
        order_by: Optional[Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters
    ) -> list[T]:
        """
        Lấy danh sách các bản ghi khớp với bộ lọc (có sắp xếp và phân trang).
        Tương đương: findAll({ where: { ... }, limit, offset }).
        """
        stmt = select(self.model).filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        stmt = self._apply_options(stmt, include)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def find_page(
        self,
        *expressions,
        order_by: Optional[Any] = None,
        page: int = 1,
        limit: int = 10,
        include: Optional[list] = None,
        **filters
    ) -> tuple[list[T], int]:
        """
        Truy vấn danh sách phân trang (Page Pagination) kèm đếm tổng số bản ghi:
        - Hỗ trợ cả filter chính xác (**filters) và biểu thức nâng cao (*expressions: ilike, in_, v.v.).
        """
        stmt = select(self.model).filter_by(**filters)
        if expressions:
            stmt = stmt.where(*expressions)

        # 1. Đếm tổng số bản ghi thỏa mãn
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        # 2. Phân trang và sắp xếp
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        offset = max(0, (page - 1) * limit)
        stmt = stmt.offset(offset).limit(limit)
        stmt = self._apply_options(stmt, include)

        res = await self.db.execute(stmt)
        return list(res.scalars().all()), total

    async def count(self, **filters) -> int:
        """Đếm số lượng bản ghi thỏa mãn điều kiện."""
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def exists(self, **filters) -> bool:
        """Kiểm tra sự tồn tại của bản ghi theo điều kiện."""
        c = await self.count(**filters)
        return c > 0

    async def create(self, **data) -> T:
        """
        Tạo mới và lưu 1 bản ghi vào Database.
        Tương đương: Model.create({ ... }).
        """
        item = self.model(**data)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update(self, id: Any, **data) -> Optional[T]:
        """
        Cập nhật dữ liệu cho 1 bản ghi theo ID.
        Tương đương: Model.update({ ... }, { where: { id } }).
        """
        item = await self.find_by_id(id)
        if not item:
            return None
        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, id: Any, soft: bool = True) -> bool:
        """
        Xóa bản ghi (mặc định xóa mềm nếu Model có trường is_deleted).
        """
        item = await self.find_by_id(id)
        if not item:
            return False
        if soft and hasattr(item, "is_deleted"):
            item.is_deleted = True
            if hasattr(item, "deleted_at"):
                item.deleted_at = datetime.now()
        else:
            await self.db.delete(item)
        await self.db.commit()
        return True
