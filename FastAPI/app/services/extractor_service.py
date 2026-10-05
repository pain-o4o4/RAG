import os
from pathlib import Path
from langchain_core.documents import Document as LangchainDocument
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader

from app.core.exceptions import InvalidFileException


class ExtractorService:
    """
    Service trích xuất nội dung văn bản từ các định dạng tệp sang LangChain Documents:
    - PDF: Sử dụng PyPDFLoader đọc nội dung theo từng trang kèm metadata số trang.
    - DOCX: Sử dụng Docx2txtLoader đọc các đoạn văn bản.
    - TXT: Sử dụng TextLoader với tính năng autodetect_encoding.
    """

    @staticmethod
    def load_document(file_path: str) -> list[LangchainDocument]:
        """
        Đọc và trích xuất file vật lý thành danh sách LangChain Documents.
        """
        if not os.path.exists(file_path):
            raise InvalidFileException(f"Tệp tin không tồn tại: {file_path}")

        ext = Path(file_path).suffix.lower()

        try:
            if ext == ".pdf":
                loader = PyPDFLoader(file_path)
            elif ext in [".docx", ".doc"]:
                loader = Docx2txtLoader(file_path)
            elif ext == ".txt":
                loader = TextLoader(file_path, autodetect_encoding=True)
            else:
                raise InvalidFileException(f"Định dạng tệp '{ext}' chưa được hỗ trợ trích xuất.")

            docs = loader.load()

            # Lọc bỏ các trang rỗng không có chữ
            non_empty_docs = [d for d in docs if d.page_content and d.page_content.strip()]
            if not non_empty_docs:
                raise InvalidFileException("Tệp tin rỗng hoặc không chứa văn bản có thể trích xuất")

            return non_empty_docs

        except InvalidFileException:
            raise
        except Exception as e:
            raise InvalidFileException(f"Lỗi khi đọc file '{Path(file_path).name}': {str(e)}")
