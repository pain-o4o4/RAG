# TÀI LIỆU KIẾN TRÚC & HƯỚNG DẪN CODEBASE CHI TIẾT (DEVELOPER GUIDE)

## DỰ ÁN: FASTAPI RAG SYSTEM (RETRIEVAL-AUGMENTED GENERATION)

---

## 1. CẤU TRÚC THƯ MỤC CHUẨN CỦA DỰ ÁN

```text
fastAPI/
├── .env                        # Biến môi trường cấu hình hệ thống
├── .env.example                # Mẫu biến môi trường
├── requirements.txt            # Danh sách thư viện Python phụ thuộc
├── storage/                    # Thư mục chứa dữ liệu cục bộ
│   ├── uploads/                # File tài liệu tải lên (PDF, DOCX, TXT) theo user
│   └── vector_store/           # File FAISS index (.index) và metadata (.json)
└── app/
    ├── __init__.py             # Module root
    ├── main.py                 # Entrypoint khởi chạy ứng dụng FastAPI & Lifespan
    ├── core/                   # Cấu hình lõi & hạ tầng
    │   ├── __init__.py
    │   ├── config.py           # Pydantic Settings đọc biến môi trường .env
    │   ├── database.py         # Cấu hình SQLAlchemy Async Engine & Session
    │   └── security.py         # Logic băm mật khẩu (Bcrypt)
    ├── models/                 # SQLAlchemy ORM Models (Định nghĩa bảng DB)
    │   ├── __init__.py
    │   ├── user.py             # Bảng users
    │   ├── document.py         # Bảng documents
    │   └── chat.py             # Bảng chat_sessions và chat_messages
    ├── schemas/                # Pydantic Schemas (Request / Response validation)
    │   ├── __init__.py
    │   ├── auth.py             # Schema UserCreate, UserLogin, UserResponse
    │   ├── document.py         # Schema DocumentResponse
    │   └── chat.py             # Schema QueryRequest, QueryResponse, Citations
    ├── services/               # Tầng nghiệp vụ cốt lõi & RAG Engine
    │   ├── __init__.py
    │   ├── extractor_service.py# Đọc nội dung file PDF, DOCX, TXT
    │   ├── chunking_service.py # Cắt nhỏ văn bản (sliding window)
    │   ├── embedding_service.py# Vector hóa văn bản bằng Google text-embedding-004
    │   ├── vector_store.py     # Quản lý FAISS index theo từng User
    │   └── rag_engine.py       # Phối hợp Retrieval + Prompt + Gemini LLM
    └── routers/                # Tầng API Endpoints (Controllers)
        ├── __init__.py         # Gom tất cả routers thành master api_router
        ├── deps.py             # Dependency Injection lấy user qua Header X-User-Id
        └── v1/
            ├── __init__.py
            ├── auth.py         # API đăng ký, đăng nhập, thông tin user
            ├── document.py     # API upload, xem danh sách, xóa tài liệu
            └── chat.py         # API đặt câu hỏi RAG & lưu lịch sử
```

---

## 2. CHI TIẾT TỪNG TẦNG VÀ ĐƯỜNG DẪN CODE

### 2.1 Tầng Cấu Hình Lõi (`app/core/`)

#### 1. `app/core/config.py`

- **Mục đích:** Quản lý toàn bộ cấu hình, siêu tham số của RAG và các biến môi trường thông qua `pydantic-settings`.
- **Nhiệm vụ:** Tự động tạo các thư mục lưu trữ (`uploads`, `vector_store`) nếu chưa tồn tại.

```python
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI RAG System"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str

    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_MODEL: str = "gemini-2.5-flash"

    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    VECTOR_STORE_DIR: str = "./storage/vector_store"

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 4
    SIMILARITY_THRESHOLD: float = 0.45

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
```

#### 2. `app/core/database.py`

- **Mục đích:** Cung cấp kết nối bất đồng bộ (Async) tới cơ sở dữ liệu và Dependency `get_db`.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

#### 3. `app/core/security.py`

- **Mục đích:** Cung cấp tiện ích mã hoá mật khẩu một chiều bằng thuật toán `bcrypt`.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

---

### 2.2 Tầng Cơ Sở Dữ Liệu (`app/models/`)

- **`app/models/user.py`:** Lưu thông tin người dùng với `id` là UUID v4.
- **`app/models/document.py`:** Lưu metadata tài liệu liên kết với người dùng (`user_id = ForeignKey('users.id')`).
- **`app/models/chat.py`:** Lưu phiên chat (`ChatSession`) và từng tin nhắn kèm danh sách trích dẫn `sources` dạng JSON (`ChatMessage`).

---

### 2.3 Tầng Schema & DTO (`app/schemas/`)

- **`app/schemas/auth.py`:** `UserCreate` (username, password), `UserLogin`, `UserResponse` (id UUID, username, created_at).
- **`app/schemas/document.py`:** `DocumentResponse` (id, filename, file_type, file_size, created_at).
- **`app/schemas/chat.py`:**
  - `SourceCitation`: Chứa `document_id`, `filename`, `content_snippet`, `similarity_score`.
  - `QueryRequest`: Chứa `question`, `session_id`.
  - `QueryResponse`: Chứa `session_id`, `question`, `answer`, `sources`.

---

### 2.4 Tầng Xử Lý Nghiệp Vụ & RAG (`app/services/`)

#### 1. `app/services/extractor_service.py`

- Dùng `pypdf` đọc PDF, `python-docx` đọc DOCX, và file I/O đọc TXT.

#### 2. `app/services/chunking_service.py`

- Thuật toán Sliding Window với kích thước `CHUNK_SIZE` và độ gối đầu `CHUNK_OVERLAP`, ưu tiên ngắt tại dấu chấm câu (`. `, `\n`).

#### 3. `app/services/embedding_service.py`

- Sử dụng Google GenAI SDK (`google.genai.Client`) gọi model `text-embedding-004` chuyển văn bản thành vector 768 chiều.

#### 4. `app/services/vector_store.py`

- Quản lý FAISS Vector Store riêng biệt cho từng User (`user_{uuid}.index` và `user_{uuid}_meta.json`).
- Sử dụng `IndexFlatIP` kết hợp chuẩn hoá $L_2$ (`faiss.normalize_L2`) để tính toán Cosine Similarity.
- Hỗ trợ xóa vector theo `document_id`.

#### 5. `app/services/rag_engine.py`

- Điểm mấu chốt của RAG:
  1. Vector hóa câu hỏi.
  2. Tìm kiếm Top-K vector gần nhất trong FAISS.
  3. Lọc bỏ các kết quả có điểm tương đồng dưới `SIMILARITY_THRESHOLD`.
  4. Nếu không có đoạn văn nào phù hợp $\to$ Trả về thông báo tiêu chuẩn *"Tôi không tìm thấy thông tin phù hợp..."*.
  5. Nếu có đoạn văn phù hợp $\to$ Đóng gói Prompt ép LLM chỉ trả lời dựa trên ngữ cảnh $\to$ Gọi `gemini-2.5-flash` sinh phản hồi kèm danh sách trích dẫn.

---

### 2.5 Tầng Điều Khiển API (`app/routers/`)

- **`app/routers/deps.py`:** Trích xuất và xác thực `x_user_id` từ Request Header `X-User-Id`.
- **`app/routers/v1/auth.py`:** Đăng ký tài khoản, đăng nhập trả về thông tin user.
- **`app/routers/v1/document.py`:** Upload file, lưu đĩa, gọi pipeline trích xuất $\to$ chunking $\to$ embedding $\to$ FAISS. Hỗ trợ xóa tài liệu và xóa index.
- **`app/routers/v1/chat.py`:** Tiếp nhận câu hỏi, tạo session, gọi `RAGEngine` và lưu lịch sử vào DB.
- **`app/routers/__init__.py`:** Gom tất cả module routers vào `api_router`.

---

## 3. HƯỚNG DẪN KHỞI CHẠY & KIỂM THỬ HỆ THỐNG

### 3.1 Khởi chạy Server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 3.2 Kịch bản kiểm thử mẫu (Test Flow)

1. **Bước 1: Đăng ký tài khoản**

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123"}'
   ```
   *(Lấy `id` UUID từ kết quả trả về, ví dụ: `d290f1ee-6c54-4b01-90e6-d701748f0851`)*
2. **Bước 2: Tải lên tài liệu mẫu (PDF / DOCX / TXT)**

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/documents/upload \
     -H "X-User-Id: d290f1ee-6c54-4b01-90e6-d701748f0851" \
     -F "file=@/path/to/sample_document.pdf"
   ```
3. **Bước 3: Đặt câu hỏi đúng nội dung tài liệu**

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/chat/query \
     -H "Content-Type: application/json" \
     -H "X-User-Id: d290f1ee-6c54-4b01-90e6-d701748f0851" \
     -d '{"question": "Nội dung chính của tài liệu này là gì?"}'
   ```
4. **Bước 4: Đặt câu hỏi không có trong tài liệu (Kiểm tra chống Hallucination)**

   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/chat/query \
     -H "Content-Type: application/json" \
     -H "X-User-Id: d290f1ee-6c54-4b01-90e6-d701748f0851" \
     -d '{"question": "Cho tôi biết công thức chế tạo thuốc nổ TNT?"}'
   ```
   *Kết quả mong đợi:* Hệ thống trả về câu thông báo không tìm thấy thông tin trong tài liệu tải lên.
