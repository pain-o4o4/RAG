import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.vector_store import VectorStore
from app.core.config import settings
from app.core.exceptions import (
    InvalidFileException,
    DocumentNotFoundException,
    DocumentAlreadyExistsException,
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # Giới hạn 50MB


class DocumentService:
    """
    Tầng Service quản lý tài liệu và tích hợp RAG Pipeline:
    - Tiếp nhận file upload, kiểm tra định dạng và kích thước.
    - Tính mã băm SHA256 chống tải file trùng lặp.
    - Lưu trữ file vật lý trên đĩa.
    - Trích xuất nội dung (PDF, DOCX, TXT), Chunking, Embedding và nạp FAISS.
    - Truy vấn, phân trang và xóa mềm bản ghi trong Database.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _process_document_rag(self, doc: Document) -> None:
        """
        Quy trình ETL RAG tự động cho tài liệu bằng LangChain:
        1. Trích xuất text từ file vật lý (PDF, DOCX, TXT) bằng LangChain DocumentLoaders.
        2. Cắt nhỏ thành các chunks bằng RecursiveCharacterTextSplitter.
        3. Tạo vector embeddings và nạp vào Vector Database FAISS.
        4. Lưu thông tin các DocumentChunk vào PostgreSQL.
        5. Cập nhật Document.status = "COMPLETED" (hoặc "FAILED" nếu có lỗi).
        """
        try:
            doc.status = "PROCESSING"
            await self.db.commit()

            # 1. & 2. Trích xuất text và phân đoạn (Langchain loaders & text splitter)
            ext = Path(doc.file_path).suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(doc.file_path)
            elif ext in [".docx", ".doc"]:
                loader = Docx2txtLoader(doc.file_path)
            elif ext == ".txt":
                loader = TextLoader(doc.file_path, autodetect_encoding=True)
            else:
                raise ValueError("Unsupported extension")
                
            documents = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                separators=["\n\n", "\n", ".", "?", "!", " ", ""]
            )
            split_docs = text_splitter.split_documents(documents)
            
            # Gán thêm metadata để liên kết chunk_index
            for i, d in enumerate(split_docs):
                d.metadata["document_id"] = str(doc.id)
                d.metadata["chunk_index"] = i
                if "page" in d.metadata:
                    d.metadata["page_number"] = d.metadata["page"] + 1

            # 3. Nạp vào Vector Database FAISS (FAISS Wrapper)
            vector_store = VectorStore()
            vector_ids = vector_store.add_documents(
                user_id=doc.user_id,
                documents=split_docs
            )

            # 4. Lưu DocumentChunk vào DB
            for i, (d, v_id) in enumerate(zip(split_docs, vector_ids)):
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    content=d.page_content,
                    vector_id=v_id,
                    chunk_metadata=d.metadata,
                    token_count=max(1, len(d.page_content) // 4),
                )
                self.db.add(db_chunk)

            # 5. Cập nhật trạng thái hoàn thành
            doc.status = "COMPLETED"
            doc.chunk_count = len(split_docs)
            doc.error_message = None
            await self.db.commit()
            await self.db.refresh(doc)
        except Exception as e:
            doc.status = "FAILED"
            doc.error_message = str(e)
            await self.db.commit()
            await self.db.refresh(doc)

    async def upload_document(self, file: UploadFile, user_id: uuid.UUID) -> Document:
        """
        Nghiệp vụ tải lên tài liệu mới:
        1. Kiểm tra phần mở rộng (.pdf, .docx, .txt).
        2. Đọc nội dung và kiểm tra kích thước file (tối đa 50MB).
        3. Tính toán SHA256 để chống trùng lặp.
        4. Ghi file an toàn vào thư mục storage/uploads.
        5. Tạo bản ghi Document và kích hoạt RAG pipeline tự động.
        """
        if not file.filename:
            raise InvalidFileException("Tên tệp tin không hợp lệ")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileException(
                f"Định dạng tệp '{ext}' không được hỗ trợ. Hệ thống chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise InvalidFileException("Tệp tin rỗng, không chứa dữ liệu")

        if file_size > MAX_FILE_SIZE:
            raise InvalidFileException("Kích thước tệp vượt quá giới hạn tối đa cho phép (50MB)")

        # Tính toán hash SHA256
        file_hash = hashlib.sha256(content).hexdigest()

        # Kiểm tra file đã tồn tại với user này chưa
        query = select(Document).where(
            Document.user_id == user_id,
            Document.file_hash == file_hash,
            Document.is_deleted == False
        )
        result = await self.db.execute(query)
        existing_doc = result.scalars().first()
        if existing_doc:
            raise DocumentAlreadyExistsException(
                f"Tài liệu '{file.filename}' đã tồn tại trong danh sách của bạn"
            )

        # Lưu file vật lý vào thư mục storage/uploads
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        safe_filename = f"{uuid.uuid4().hex[:12]}_{Path(file.filename).name}"
        saved_file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

        with open(saved_file_path, "wb") as f:
            f.write(content)

        # Tạo bản ghi vào Database
        new_document = Document(
            filename=file.filename,
            file_path=saved_file_path,
            file_size=file_size,
            file_type=(file.content_type or ext.lstrip("."))[:100],
            file_hash=file_hash,
            status="PENDING",
            chunk_count=0,
            user_id=user_id,
        )

        self.db.add(new_document)
        await self.db.commit()
        await self.db.refresh(new_document)

        # Kích hoạt xử lý RAG
        await self._process_document_rag(new_document)

        return new_document


    async def upload_multiple_documents(
        self,
        files: list[UploadFile],
        user_id: uuid.UUID
    ) -> dict:
        """
        Nghiệp vụ tải lên nhiều tài liệu cùng lúc (Batch Upload):
        - Xử lý kiên cường (Resilient): file hợp lệ thì lưu, file lỗi thì ghi nhận lý do.
        - Chống trùng lặp (SHA256) cả với Database và giữa các file trong cùng mẻ.
        - Trả về tổng kết: total_uploaded, total_failed, uploaded, failed.
        """
        if not files or len(files) == 0:
            raise InvalidFileException("Vui lòng chọn ít nhất một tệp tin để tải lên")

        # Lấy trước danh sách hash đã có của user để tối ưu tốc độ so sánh
        existing_hashes_query = select(Document.file_hash).where(
            Document.user_id == user_id,
            Document.is_deleted == False,
            Document.file_hash.isnot(None)
        )
        existing_hashes_res = await self.db.execute(existing_hashes_query)
        known_hashes = set(existing_hashes_res.scalars().all())

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        uploaded_docs: list[Document] = []
        failed_items: list[dict] = []
        seen_in_batch: set[str] = set()

        for file in files:
            fname = file.filename or "unknown"

            # 1. Kiểm tra định dạng đuôi file
            ext = Path(fname).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                failed_items.append({
                    "filename": fname,
                    "reason": f"Định dạng '{ext}' không được hỗ trợ (chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)})"
                })
                continue

            # 2. Đọc nội dung & kiểm tra dung lượng
            content = await file.read()
            file_size = len(content)
            if file_size == 0:
                failed_items.append({
                    "filename": fname,
                    "reason": "Tệp tin rỗng, không chứa dữ liệu"
                })
                continue

            if file_size > MAX_FILE_SIZE:
                failed_items.append({
                    "filename": fname,
                    "reason": "Kích thước tệp vượt quá giới hạn 50MB"
                })
                continue

            # 3. Tính băm SHA256 & kiểm tra trùng lặp
            file_hash = hashlib.sha256(content).hexdigest()
            if file_hash in seen_in_batch:
                continue

            if file_hash in known_hashes:
                # Tài liệu đã tồn tại trong DB của user, tái sử dụng để liên kết session
                exist_q = select(Document).where(
                    Document.user_id == user_id,
                    Document.file_hash == file_hash,
                    Document.is_deleted == False
                )
                exist_res = await self.db.execute(exist_q)
                existing_doc = exist_res.scalars().first()
                if existing_doc:
                    seen_in_batch.add(file_hash)
                    uploaded_docs.append(existing_doc)
                    continue

            seen_in_batch.add(file_hash)
            known_hashes.add(file_hash)

            # 4. Ghi file vào thư mục storage/uploads
            safe_filename = f"{uuid.uuid4().hex[:12]}_{Path(fname).name}"
            saved_file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

            with open(saved_file_path, "wb") as f:
                f.write(content)

            # 5. Tạo đối tượng Document
            new_doc = Document(
                filename=fname,
                file_path=saved_file_path,
                file_size=file_size,
                file_type=(file.content_type or ext.lstrip("."))[:100],
                file_hash=file_hash,
                status="PENDING",
                chunk_count=0,
                user_id=user_id,
            )
            self.db.add(new_doc)
            uploaded_docs.append(new_doc)

        # 6. Commit các tài liệu hợp lệ và kích hoạt xử lý RAG
        if uploaded_docs:
            await self.db.commit()
            for doc in uploaded_docs:
                await self.db.refresh(doc)
                if doc.status == "PENDING":
                    await self._process_document_rag(doc)

        return {
            "total_uploaded": len(uploaded_docs),
            "total_failed": len(failed_items),
            "uploaded": uploaded_docs,
            "failed": failed_items,
        }


    async def get_documents(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[list[Document], int]:
        """
        Nghiệp vụ lấy danh sách tài liệu có lọc và phân trang:
        - Lọc theo user_id và chỉ lấy tài liệu chưa bị xóa mềm.
        - Tùy chọn lọc theo status (PENDING, PROCESSING, COMPLETED, FAILED).
        - Tùy chọn tìm kiếm theo tên tệp (filename).
        """
        base_query = select(Document).where(
            Document.user_id == user_id,
            Document.is_deleted == False
        )

        if status:
            base_query = base_query.where(Document.status == status.upper())

        if search:
            base_query = base_query.where(Document.filename.ilike(f"%{search.strip()}%"))

        # Đếm tổng số bản ghi
        count_query = select(func.count()).select_from(base_query.subquery())
        count_res = await self.db.execute(count_query)
        total = count_res.scalar() or 0

        # Lấy dữ liệu theo trang
        offset = (page - 1) * limit
        items_query = (
            base_query.order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_res = await self.db.execute(items_query)
        items = items_res.scalars().all()

        return list(items), total

    async def get_document_by_id(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> Document:
        """
        Nghiệp vụ lấy chi tiết 1 tài liệu:
        - Đảm bảo tài liệu tồn tại, chưa bị xóa và thuộc quyền sở hữu của user.
        """
        query = select(Document).where(
            Document.id == doc_id,
            Document.user_id == user_id,
            Document.is_deleted == False
        )
        result = await self.db.execute(query)
        doc = result.scalars().first()

        if not doc:
            raise DocumentNotFoundException("Tài liệu không tồn tại hoặc bạn không có quyền truy cập")

        return doc

    async def delete_document(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> Document:
        """
        Nghiệp vụ xóa mềm (Soft Delete) tài liệu:
        - Đánh dấu is_deleted = True và cập nhật deleted_at = now().
        """
        doc = await self.get_document_by_id(doc_id, user_id)
        doc.is_deleted = True
        doc.deleted_at = datetime.now()

        await self.db.commit()
        return doc
