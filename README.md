# Hệ Thống RAG (Retrieval-Augmented Generation) & AI Agent Platform

Hệ thống **RAG Fullstack** chuyên nghiệp cho phép người dùng tải lên và quản lý các tài liệu tri thức (`.pdf`, `.docx`, `.txt`), tự động băm nhỏ và số hóa ngữ nghĩa qua **Google Gemini Embeddings**, lưu trữ vào **FAISS Vector Database**, và thực hiện hỏi đáp thông minh theo ngữ cảnh thực tế với **Google Gemini LLM** (tuân thủ nghiêm ngặt nguyên tắc **Zero-Hallucination** - Không bịa đặt khi thiếu dữ kiện).

---

## MỤC LỤC

1. [Tính năng nổi bật](#-1-tính-năng-nổi-bật)
2. [Kiến trúc &amp; Công nghệ sử dụng](#-2-kiến-trúc--công-nghệ-sử-dụng)
3. [Cấu trúc thư mục dự án](#-3-cấu-trúc-thư-mục-dự-án)
4. [Yêu cầu tiên quyết (Prerequisites)](#-4-yêu-cầu-tiên-quyết-prerequisites)
5. [Hướng dẫn cài đặt Cơ sở dữ liệu (PostgreSQL)](#-5-hướng-dẫn-cài-đặt-cơ-sở-dữ-liệu-postgresql)
6. [Hướng dẫn cài đặt &amp; Cấu hình Backend (FastAPI)](#-6-hướng-dẫn-cài-đặt--cấu-hình-backend-fastapi)
7. [Hướng dẫn cài đặt &amp; Cấu hình Frontend (ReactJS)](#-7-hướng-dẫn-cài-đặt--cấu-hình-frontend-reactjs)
8. [Khởi chạy toàn bộ hệ thống](#-8-khởi-chạy-toàn-bộ-hệ-thống)
9. [Tài liệu API &amp; Hướng dẫn Kiểm thử](#-9-tài-liệu-api--hướng-dẫn-kiểm-thử)
10. [Giải thích các tham số cấu hình RAG](#-10-giải-thích-các-tham-số-cấu-hình-rag)
11. [Xử lý trường hợp không có thông tin trong tri thức](#-11-xử-lý-trường-hợp-không-có-thông-tin-trong-tri-thức)
12. [Xử lý sự cố thường gặp (Troubleshooting)](#-12-xử-lý-sự-cố-thường-gặp-troubleshooting)

---

## 1. TÍNH NĂNG NỔI BẬT

- **Multi-format Document Ingestion**: Hỗ trợ trích xuất văn bản tự động từ PDF, Word (`.docx`), và Text thuần (`.txt`).
- **Deduplication bằng SHA-256**: Tự động băm `file_hash` để phát hiện và ngăn ngừa trùng lặp tài liệu, tiết kiệm chi phí tính toán embedding.
- **Semantic Chunking**: Phân đoạn văn bản thông minh bằng `RecursiveCharacterTextSplitter` với kích thước `1200` ký tự và độ gối đầu `200` ký tự giúp bảo toàn ngữ cảnh.
- **Google Gemini Embeddings**: Chuyển đổi văn bản thành vector đặc trưng chuẩn hóa 3072 chiều.
- **FAISS Vector Index per-user**: Lưu trữ và tìm kiếm vector cục bộ hiệu năng cao theo từng tài khoản người dùng (`{user_id}.faiss` và `{user_id}.pkl`).
- **Zero-Hallucination Prompt Engineering**: Ràng buộc mô hình LLM (`gemini-3.7-flash`) chỉ trả lời dựa trên tài liệu thực tế, từ chối võ đoán khi thiếu dữ kiện.
- **Multi-turn Chat & Trích dẫn nguồn**: Quản lý lịch sử hội thoại nhiều lượt, hỗ trợ đính kèm tài liệu vào từng phiên chat và hiển thị rõ ràng nguồn trích dẫn (`document_id`, `chunk_index`, `page_number`).
- **Giao diện Modern React**: Giao diện trực quan, hỗ trợ hiển thị Markdown, code block, hiệu ứng gõ và quản lý tài liệu linh hoạt.

---

## 2. KIẾN TRÚC & CÔNG NGHỆ SỬ DỤNG

### Sơ đồ kiến trúc tổng thể:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   KIẾN TRÚC TỔNG THỂ                                  │
│                                                                                        │
│   [ ReactJS Frontend ] (Port 3000)                                                     │
│            │                                                                           │
│            ▼ HTTP RESTful API / JSON                                                   │
│   [ FastAPI Backend ] (Port 8000)                                                      │
│      ├── SQLAlchemy 2.0 (Asyncio) ──► [ PostgreSQL ] (orbit_db / Port 5432)            │
│      ├── Extractor & Chunking (LangChain)                                              │
│      ├── Google Gemini Embeddings (768-dim) ──► [ FAISS Vector Store ] (Local Disk)    │
│      └── RAG Engine & Anti-Hallucination ──► [ Google Gemini 3.7 Flash LLM ]           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Công nghệ sử dụng:

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.0 (Asyncpg), Pydantic v2, Passlib/Bcrypt.
- **AI & RAG Engine**: LangChain, FAISS CPU, Google GenAI SDK (`gemini-3.7-flash`, `gemini-embedding-2`).
- **Frontend**: React 18, React Router v6, Redux / Redux-Thunk, SASS, Axios, React Markdown.
- **Database**: PostgreSQL 16 (Docker Container `orbit-postgres`).

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
RAG/
├── FastAPI/                    # Mã nguồn Backend FastAPI
│   ├── app/
│   │   ├── core/               # Cấu hình hệ thống, Database, Security, Repository
│   │   │   ├── config.py       # Pydantic BaseSettings (Đọc file .env)
│   │   │   ├── database.py     # Khởi tạo Async Engine & SessionMaker
│   │   │   ├── repository.py   # BaseRepository Generic Pattern (find_page, CRUD)
│   │   │   └── security.py     # Hash & kiểm tra mật khẩu (Bcrypt)
│   │   ├── models/             # SQLAlchemy ORM Models (6 bảng quan hệ)
│   │   │   ├── user.py         # Bảng users
│   │   │   ├── document.py     # Bảng documents (metadata & file_hash)
│   │   │   ├── document_chunk.py # Bảng document_chunks (text & chunk_index)
│   │   │   ├── chat_session.py # Bảng chat_sessions
│   │   │   ├── chat_message.py # Bảng chat_messages (lịch sử & sources trích dẫn)
│   │   │   └── session_document.py # Bảng quan hệ Many-to-Many
│   │   ├── routers/            # API Endpoints (v1)
│   │   │   └── v1/
│   │   │       ├── auth.py     # Đăng ký, Đăng nhập
│   │   │       ├── documents.py# Upload, danh sách, chi tiết, xóa tài liệu
│   │   │       └── chat.py     # Chat, hỏi đáp RAG, quản lý session
│   │   ├── schemas/            # Pydantic Schemas (DTO validation)
│   │   ├── services/           # Nghiệp vụ lõi (Single Responsibility Pattern)
│   │   │   ├── extractor_service.py # Đọc file PDF, DOCX, TXT
│   │   │   ├── chunking_service.py  # Cắt nhỏ văn bản (Recursive Text Splitter)
│   │   │   ├── embedding_service.py # GeminiEmbeddings chuẩn 768 chiều
│   │   │   ├── vector_store.py      # Quản lý kho FAISS Index theo User
│   │   │   ├── document_service.py  # Điều phối upload & ETL RAG
│   │   │   ├── rag_service.py       # RAG Retrieval, Prompting & Gemini LLM
│   │   │   └── chat_service.py      # Điều phối hội thoại & lưu tin nhắn
│   │   └── main.py             # Entrypoint khởi tạo FastAPI Application
│   ├── storage/                # Lưu trữ file vật lý & FAISS index (Tự tạo)
│   │   ├── uploads/            # Chứa các file PDF/DOCX đã tải lên
│   │   └── vector_store/       # Chứa các file {user_id}.faiss và {user_id}.pkl
│   ├── .env.example            # File mẫu cấu hình môi trường Backend
│   ├── .env                    # Biến môi trường thực tế (Bảo mật - Không đẩy lên Git)
│   └── requirements.txt        # Danh sách thư viện Python
├── FE/                         # Mã nguồn Frontend ReactJS
│   ├── src/                    # Components, Redux Actions/Reducers, Styles
│   ├── public/                 # Static assets (HTML, Icons)
│   ├── .env.example            # File mẫu cấu hình môi trường Frontend
│   ├── .env                    # Biến môi trường Frontend thực tế
│   └── package.json            # Danh sách thư viện NPM & Scripts
├── DS_Store/                   # Tài liệu kiến trúc & kịch bản RAG chuyên sâu
│   ├── RAG.md                  # Tài liệu chi tiết kiến trúc và luồng xử lý
│   └── RAG_flow.md             # Kịch bản 4 ca sử dụng thực tế (Walkthrough)
├── .gitignore                  # Cấu hình loại trừ file nhạy cảm và build artifacts
└── README.md                   # Tài liệu hướng dẫn dự án (File này)
```

---

## 4. YÊU CẦU TIÊN QUYẾT (PREREQUISITES)

Trước khi bắt đầu, đảm bảo máy tính của bạn đã cài đặt các công cụ sau:

- **Python**: Phiên bản `>= 3.10` (Khuyên dùng `Python 3.11`).
- **Node.js**: Phiên bản `>= 18.x` và `npm` `>= 9.x`.
- **Docker** *(Khuyên dùng)*: Để khởi chạy PostgreSQL container nhanh chóng.
- **Google Gemini API Key**: Đăng ký và lấy API Key miễn phí tại [Google AI Studio](https://aistudio.google.com/).

---

## 5. HƯỚNG DẪN CÀI ĐẶT CƠ SỞ DỮ LIỆU (POSTGRESQL)

Hệ thống sử dụng cơ sở dữ liệu **PostgreSQL** với tên database là **`orbit_db`**.

### Cách 1: Chạy bằng Docker (Khuyên dùng - Nhanh nhất)

Chạy lệnh sau trên terminal để tạo và khởi động container:

```bash
docker run --name orbit-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgrespassword \
  -e POSTGRES_DB=orbit_db \
  -p 5432:5432 \
  -d postgres:16-alpine
```

Kiểm tra container đang chạy:

```bash
docker ps
```

*(Nếu đã có container `orbit-postgres` từ trước, chỉ cần chạy `docker start orbit-postgres`).*

### Cách 2: Sử dụng PostgreSQL cài sẵn trên máy (Native)

Nếu bạn dùng PostgreSQL cài trực tiếp trên máy, hãy mở `psql` và tạo database `orbit_db`:

```sql
CREATE DATABASE orbit_db;
```

---

## 6. HƯỚNG DẪN CÀI ĐẶT & CẤU HÌNH BACKEND (FASTAPI)

### Bước 1: Mở thư mục Backend và tạo môi trường ảo Python

```bash
cd FastAPI

# Tạo môi trường ảo .venv
python3 -m venv .venv

# Kích hoạt môi trường ảo:
# Trên macOS / Linux:
source .venv/bin/activate

# Trên Windows (Command Prompt):
.venv\Scripts\activate.bat

# Trên Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt các thư viện phụ thuộc

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 3: Tạo và cấu hình file `.env`

Sao chép file mẫu `.env.example` thành `.env`:

```bash
cp .env.example .env
```

Mở file `.env` vừa tạo và điền các giá trị chính xác:

```env
PROJECT_NAME="RAG Backend API"
API_V1="/api/v1"
API_V1_STR="/api/v1"

# Cấu hình Database kết nối tới PostgreSQL (Asyncpg)
DATABASE_URL="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/orbit_db"

# Google Gemini API Key (Điền key thực tế của bạn)
GEMINI_API_KEY="AIzaSyYourActualGeminiApiKeyHere"
EMBEDDING_MODEL="gemini-embedding-2"
LLM_MODEL="gemini-3.7-flash"

# Thư mục lưu trữ
STORAGE_DIR="./storage"
UPLOAD_DIR="./storage/uploads"
VECTOR_STORE_DIR="./storage/vector_store"

# Cấu hình phân đoạn & Tìm kiếm RAG
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
TOP_K_RESULTS=8
SIMILARITY_THRESHOLD=0.20
EMBEDDING_DIMENSION=768
MAX_FILE_SIZE=52428800
```

> [!NOTE]
> Khi Backend khởi động lần đầu, hệ thống sẽ **tự động khởi tạo toàn bộ 6 bảng cơ sở dữ liệu** thông qua cơ chế SQLAlchemy Async Lifespan Handler mà không cần chạy lệnh migration thủ công.

---

## 7. HƯỚNG DẪN CÀI ĐẶT & CẤU HÌNH FRONTEND (REACTJS)

### Bước 1: Mở thư mục Frontend

Mở một cửa sổ Terminal mới:

```bash
cd FE
```

### Bước 2: Tạo file `.env` Frontend

Sao chép file mẫu `.env.example` thành `.env`:

```bash
cp .env.example .env
```

Nội dung file `.env` của Frontend:

```env
PORT=3000
REACT_APP_BACKEND_URL=http://localhost:8000
```

### Bước 3: Cài đặt các gói phụ thuộc (NPM Packages)

```bash
npm install --legacy-peer-deps
```

*(Cờ `--legacy-peer-deps` đảm bảo tương thích mượt mà giữa React 18 và các thư viện UI).*

---

## 8. KHỞI CHẠY TOÀN BỘ HỆ THỐNG

### 1. Khởi chạy Backend (FastAPI):

Tại cửa sổ Terminal thứ nhất (thư mục `FastAPI/`, đã kích hoạt `.venv`):

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Backend URL**: `http://127.0.0.1:8000`
- **Health Check**: `http://127.0.0.1:8000/health`

### 2. Khởi chạy Frontend (ReactJS):

Tại cửa sổ Terminal thứ hai (thư mục `FE/`):

```bash
npm start
```

- **Frontend Web App**: `http://localhost:3000`
- Trình duyệt sẽ tự động mở trang web RAG.

---

## 9. TÀI LIỆU API & HƯỚNG DẪN KIỂM THỬ

FastAPI tự động tạo sẵn giao diện Swagger UI và ReDoc tương tác chuẩn OpenAPI:

| Giao diện                       | Đường dẫn truy cập                                                 | Mục đích                                               |
| :------------------------------- | :---------------------------------------------------------------------- | :-------------------------------------------------------- |
| **Interactive Swagger UI** | [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)   | Kiểm thử trực tiếp và xem schema toàn bộ endpoints |
| **ReDoc Documentation**    | [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc) | Xem đặc tả tài liệu kỹ thuật chuẩn OpenAPI 3.0    |
| **Health Check API**       | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)             | Kiểm tra tình trạng kết nối Server và Database      |

### Các nhóm API chính:

#### 1. Xác thực & Tài khoản (`/api/v1/auth`):

- `POST /register`: Đăng ký tài khoản người dùng mới.
- `POST /login`: Đăng nhập hệ thống (nhận thông tin người dùng và token).

#### 2. Quản lý tài liệu (`/api/v1/documents`):

- `POST /upload`: Tải lên 1 file (`.pdf`, `.docx`, `.txt`), tự động băm nhỏ, tính embedding và lưu vào FAISS.
- `POST /upload-multiple`: Tải lên đồng thời nhiều file cùng lúc.
- `GET /`: Danh sách tài liệu của người dùng (hỗ trợ phân trang `page`, `page_size` và tìm kiếm `search`).
- `GET /{id}`: Xem chi tiết tài liệu và danh sách các chunks.
- `DELETE /{id}`: Xóa mềm tài liệu khỏi hệ thống.

#### 3. Hội thoại & RAG Chat (`/api/v1/chat`):

- `POST /sessions`: Tạo phiên chat mới (có thể liên kết sẵn danh sách tài liệu).
- `POST /sessions/upload-and-create`: Tải file tài liệu, tạo session và gửi câu hỏi ngay trong 1 bước.
- `POST /sessions/{id}/messages`: Gửi câu hỏi vào session, kích hoạt truy xuất FAISS và sinh câu trả lời có kèm trích dẫn nguồn (`sources`).
- `GET /sessions`: Lấy danh sách tất cả các phiên chat của User.
- `GET /sessions/{id}/messages`: Lấy toàn bộ lịch sử tin nhắn trong phiên chat.

---

## 10. GIẢI THÍCH CÁC THAM SỐ CẤU HÌNH RAG

Hệ thống được tối ưu hóa sẵn với các tham số chuẩn trong [`config.py`](file:///Users/pain.o4o4/Documents/RAG/FastAPI/app/core/config.py):

| Tham số                           | Giá trị tối ưu             | Ý nghĩa & Lý do chọn                                                                                                                                               |
| :--------------------------------- | :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`CHUNK_SIZE`**           | **`1200`** ký tự     | Kích thước mỗi đoạn sau khi cắt. 1200 ký tự đủ lớn để chứa trọn vẹn 1 quy trình, bảng biểu nhỏ hoặc một điều khoản hợp đồng hoàn chỉnh. |
| **`CHUNK_OVERLAP`**        | **`200`** ký tự      | Đoạn văn bản gối đầu giữa 2 chunk liền kề, giúp chống mất ngữ cảnh ở các câu nằm ngay ranh giới chia cắt.                                         |
| **`TOP_K_RESULTS`**        | **`8`** chunks         | Kéo 8 đoạn trích có độ tương đồng cao nhất vào Prompt, cung cấp$\approx 8.000$ ký tự ngữ cảnh thực tế cho mô hình.                             |
| **`SIMILARITY_THRESHOLD`** | **`0.20`**             | Ngưỡng tương đồng cosine tối thiểu. Loại bỏ triệt để các đoạn rác không liên quan trước khi đưa vào LLM.                                       |
| **`EMBEDDING_DIMENSION`**  | **`768`** chiều       | Kích thước vector nhúng chuẩn hóa L2 của Google Gemini Embedding (`gemini-embedding-2`).                                                                      |
| **`LLM_MODEL`**            | **`gemini-3.7-flash`** | Mô hình ngôn ngữ lớn thế hệ mới nhất, suy luận nhanh, chính xác cao và hỗ trợ ngữ cảnh lớn.                                                          |

---

## 11. XỬ LÝ TRƯỜNG HỢP KHÔNG CÓ THÔNG TIN TRONG TRI THỨC

Hệ thống áp dụng cơ chế bảo vệ 3 lớp để đảm bảo tính trung thực tuyệt đối (**Zero-Hallucination**):

1. **Lọc ngưỡng tương đồng (Similarity Threshold Gate)**:
   Nếu toàn bộ các vector trong kho FAISS có điểm tương đồng $< 0.20$ so với câu hỏi của người dùng, hệ thống xác định câu hỏi hoàn toàn nằm ngoài kho tri thức.
2. **Anti-Hallucination System Prompting**:
   Prompt được thiết kế nghiêm ngặt:
   ```text
   QUY TẮC BẮT BUỘC:
   1. CHỈ sử dụng thông tin có trong phần 'NGỮ CẢNH TÀI LIỆU'.
   2. KHÔNG tự suy diễn, KHÔNG dùng kiến thức ngoài tài liệu được cấp.
   3. Nếu tài liệu không chứa đủ dữ kiện để trả lời, BẮT BUỘC trả lời rõ ràng:
      'Dựa trên các tài liệu được cung cấp, hiện không có đủ thông tin để trả lời câu hỏi này.'
   ```
3. **Trích dẫn nguồn minh bạch (Source Attribution)**:
   Mỗi câu trả lời luôn đi kèm mảng `sources` chứa `document_id`, `chunk_index`, và nội dung đoạn trích thực tế để người dùng đối soát.

---

## 12. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### 1. Lỗi kết nối Database `database "orbit_db" does not exist`

- **Nguyên nhân:** Container PostgreSQL chưa tạo database `orbit_db`.
- **Khắc phục:** Mở Terminal và chạy lệnh:
  ```bash
  docker exec -it orbit-postgres psql -U postgres -c "CREATE DATABASE orbit_db;"
  ```

### 2. Lỗi `429 Resource Exhausted / Rate Limit` từ Gemini API

- **Nguyên nhân:** Gửi request liên tục vượt hạn mức của tài khoản Google AI Studio miễn phí.
- **Khắc phục:** Hệ thống đã tích hợp sẵn cơ chế **Exponential Backoff Retry** (thử lại tự động 5 lần) trong [`embedding_service.py`](file:///Users/pain.o4o4/Documents/RAG/FastAPI/app/services/embedding_service.py) và [`rag_service.py`](file:///Users/pain.o4o4/Documents/RAG/FastAPI/app/services/rag_service.py). Nếu gặp lỗi, hãy đợi vài giây rồi thử lại.

### 3. Bot trả lời ngắn hoặc cụt ý

- **Nguyên nhân:** Tài liệu được tải lên từ phiên bản cũ khi `CHUNK_SIZE` còn để 500 ký tự.
- **Khắc phục:** Tạo phiên chat mới và **tải lại tài liệu** để hệ thống tự động băm theo cấu hình mới (`CHUNK_SIZE = 1200` và `TOP_K = 8`).

### 4. Lỗi xung đột cổng `Port 8000` hoặc `Port 3000` đã được sử dụng

- **Kiểm tra tiến trình đang chiếm cổng (macOS / Linux):**
  ```bash
  lsof -i :8000
  lsof -i :3000
  ```
- **Tắt tiến trình chiếm cổng:**
  ```bash
  kill -9 <PID>
  ```
