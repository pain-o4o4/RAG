import uuid
from typing import Optional
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class ChunkingService:
    """
    Service phân đoạn văn bản (Text Chunking):
    - Chia nhỏ các LangChain Documents theo kích thước chunk_size và chunk_overlap.
    - Tự động gán metadata quan trọng: document_id, chunk_index, page_number.
    """

    @staticmethod
    def split_documents(
        documents: list[LangchainDocument],
        doc_id: Optional[uuid.UUID] = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ) -> list[LangchainDocument]:
        """
        Cắt nhỏ danh sách tài liệu LangChain thành các đoạn chunks và gán metadata.
        """
        if not documents:
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
        )

        split_docs = text_splitter.split_documents(documents)

        # Gán metadata chuẩn hóa cho từng chunk
        for i, d in enumerate(split_docs):
            if doc_id:
                d.metadata["document_id"] = str(doc_id)
            d.metadata["chunk_index"] = i
            
            # Chuẩn hóa số trang (PyPDFLoader bắt đầu từ 0)
            if "page" in d.metadata:
                d.metadata["page_number"] = d.metadata["page"] + 1
            elif "page_number" not in d.metadata:
                d.metadata["page_number"] = 1

        return split_docs
