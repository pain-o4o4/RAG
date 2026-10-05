# RAG Backend API (Retrieval-Augmented Generation System)

Hệ thống RAG Backend hoàn chỉnh được xây dựng trên nền tảng **FastAPI**, **SQLAlchemy (Async)**, **PostgreSQL**, **Vector Search (FAISS)**, và **Google Gemini GenAI**.

---

## 🌟 Tính năng chính đã hoàn thiện 100%

### 1. Quản lý tài liệu (Document Management)

- **Hỗ trợ đa định dạng:** Trích xuất tự động nội dung từ `.pdf` (`pypdf`), `.docx` (`python-docx`) và `.txt` (`utf-8`).
- **Batch Upload kiên cường (Resilient Batching):** Tải lên một hoặc nhiều tài liệu cùng lúc, file nào lỗi/trùng sẽ được gom riêng mà không làm gián đoạn các file hợp lệ khác.
- **Chống trùng lặp (Deduplication):** Sử dụng mã băm SHA256 ngăn tải lên cùng một nội dung lặp lại.
- **Quản lý danh sách & Xóa mềm:** Hỗ trợ phân trang, tìm kiếm theo tên và soft-delete bảo toàn dữ liệu.

### 2. Pipeline RAG Cốt lõi (Core RAG Engine)

- **Chunking:** Cắt nhỏ văn bản thành các đoạn theo cửa sổ trượt (Sliding Window: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`), giữ nguyên ngữ nghĩa câu.
- **Vector Embeddings:** Sử dụng mô hình gemini-embedding-2 (3072chiều) từ Google GenAI.
- **Vector Database (FAISS):** Quản lý chỉ mục vector riêng biệt cho từng người dùng, tính toán Cosine Similarity qua chuẩn hóa L2 và `IndexFlatIP`.
- **Chống Hallucination (Bịa đặt):** Áp dụng ngưỡng tương đồng (`SIMILARITY_THRESHOLD`). Nếu câu hỏi không liên quan đến tài liệu, hệ thống từ chối trả lời rõ ràng: *"Không tìm thấy thông tin phù hợp trong tài liệu đã tải lên để trả lời câu hỏi của bạn. Hệ thống tuân thủ nguyên tắc không đưa ra câu trả lời thiếu căn cứ."*
- **Trích dẫn nguồn minh bạch (Citations):** Mỗi câu trả lời của AI đều đi kèm danh sách `sources` chi tiết gồm tên tệp tin, số trang, điểm tương đồng (similarity score) và đoạn trích dẫn (snippet).

---

## 🛠️ Yêu cầu môi trường & Cài đặt

- Python >= 3.10 (Khuyến nghị 3.11 hoặc 3.12)
- PostgreSQL Database
- Quản lý gói bằng `pip` hoặc `uv`

### 1. Khởi tạo môi trường ảo

```bash
# Sử dụng venv chuẩn
python -m venv .venv

# Kích hoạt trên Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Hoặc kích hoạt trên macOS/Linux:
source .venv/bin/activate
```

*(Nếu sử dụng `uv`: `uv venv` và `uv pip install -r requirements.txt`)*

### 2. Cài đặt thư viện

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường

Tạo file `.env` từ `.env.example` và điền thông tin:

```env
PROJECT_NAME="RAG Backend API"
API_V1_STR="/api/v1"

# Database PostgreSQL Async (asyncpg)
DATABASE_URL="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/orbit_db"

# Google Gemini API Key & Models
GEMINI_API_KEY="your_actual_gemini_api_key_here"
EMBEDDING_MODEL="gemini-embedding-001"
LLM_MODEL="gemini-3.8-flash"

# RAG & Storage Settings
STORAGE_DIR="./storage"
UPLOAD_DIR="./storage/uploads"
VECTOR_STORE_DIR="./storage/vector_store"
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=4
SIMILARITY_THRESHOLD=0.20
```

### 4. Khởi chạy Server

Khi sử dụng Windows PowerShell, chạy uvicorn từ môi trường ảo `.venv`:

```powershell
# Chạy trực tiếp từ .venv:
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Hoặc kích hoạt môi trường ảo trước:
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📖 Danh sách API Endpoints (Swagger UI)

Truy cập tài liệu tương tác trực tiếp tại: **[http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)**

### 1. Authentication

- `POST /api/v1/auth/register`: Đăng ký người dùng mới (Mã hóa Bcrypt).
- `POST /api/v1/auth/login`: Xác thực tài khoản.

### 2. Document Management

- `POST /api/v1/documents/upload`: Tải lên một hoặc nhiều tài liệu (`.pdf`, `.docx`, `.txt`), tự động chạy pipeline RAG.
- `GET /api/v1/documents`: Lấy danh sách tài liệu có phân trang (`page`, `limit`), tìm kiếm (`search`), lọc trạng thái (`status`).
- `GET /api/v1/documents/{doc_id}`: Xem chi tiết tài liệu và số lượng chunks.
- `DELETE /api/v1/documents/{doc_id}`: Xóa mềm tài liệu.

### 3. Chat Sessions & Trò chuyện RAG Đa tài liệu (Web AI Experience)

- `POST /api/v1/chat/sessions/upload` **(Mới)**: Tải lên 1 hoặc nhiều tài liệu **kèm câu hỏi/prompt** ngay trong một request. Hệ thống xử lý RAG tức thì, trả lời kèm nguồn trích dẫn và khởi tạo `session_id`.
- `POST /api/v1/chat/sessions/{id}/upload` **(Mới)**: Nạp thêm 1 hoặc nhiều tài liệu vào phiên chat hiện tại (kèm câu hỏi tùy chọn). RAG sẽ tổng hợp trên **toàn bộ** tài liệu (cũ + mới).
- `POST /api/v1/chat/sessions/{id}/messages`: Tiếp tục gửi câu hỏi thuần text trong phiên chat. RAG tự động tìm kiếm trên tất cả tài liệu thuộc phiên đó.
- `GET /api/v1/chat/sessions/{id}/messages`: Xem toàn bộ lịch sử tin nhắn trong phiên chat.
- `POST /api/v1/chat/sessions`: Tạo phiên trò chuyện mới.
- `GET /api/v1/chat/sessions`: Lấy danh sách các cuộc hội thoại.
- `GET /api/v1/chat/sessions/{id}`: Xem chi tiết phiên chat cùng danh sách tài liệu gắn kèm.
- `PATCH /api/v1/chat/sessions/{id}`: Đổi tên tiêu đề phiên chat.
- `DELETE /api/v1/chat/sessions/{id}`: Xóa mềm phiên chat.
