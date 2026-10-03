# Orbit RAG System (Retrieval-Augmented Generation)

Hệ thống RAG thông minh hoàn chỉnh cho phép người dùng tải lên tài liệu đa định dạng (PDF, DOCX, TXT) và trò chuyện, hỏi đáp tương tác trực tiếp với AI (Google Gemini GenAI).

---

## 📁 Cấu trúc Dự án

```text
RAG/
├── FastAPI/                 # Backend API (FastAPI, SQLAlchemy Async, FAISS, Gemini)
│   ├── app/                 # Mã nguồn backend
│   │   ├── core/            # Config, Database, Security, Exceptions
│   │   ├── models/          # SQLAlchemy Models (User, Document, Session, Message)
│   │   ├── routers/         # API Routers (Auth, Documents, Chat)
│   │   ├── schemas/         # Pydantic DTO Schemas
│   │   └── services/        # Nghiệp vụ: RAGService, VectorStore, EmbeddingService, etc.
│   ├── requirements.txt     # Danh sách thư viện Python
│   └── README.md            # Tài liệu chi tiết Backend
│
├── FE/                      # Frontend UI (ReactJS, Redux, SCSS)
│   ├── src/                 # Mã nguồn giao diện
│   │   ├── components/      # UI Components dùng chung
│   │   ├── containers/      # ChatWorkspace, DocumentManage, Auth
│   │   ├── services/        # Gọi API sang FastAPI
│   │   └── store/           # Redux Store & Reducers
│   └── package.json         # Danh sách dependencies Frontend
│
└── .gitignore               # Cấu hình bỏ qua thư viện và dữ liệu nhạy cảm
```

---

## 🚀 Hướng dẫn Khởi chạy

### 1. Backend (FastAPI)

```powershell
cd FastAPI

# 1. Kích hoạt môi trường ảo:
.\.venv\Scripts\Activate.ps1

# 2. Khởi chạy Server Backend:
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger UI tài liệu API: **[http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)**

---

### 2. Frontend (ReactJS)

```powershell
cd FE

# 1. Cài đặt dependencies (lần đầu):
npm install

# 2. Khởi chạy ứng dụng:
npm start
```
- Giao diện người dùng: **[http://localhost:3000](http://localhost:3000)**

---

## 🌟 Tính năng nổi bật
- **Tải tệp & Hỏi đáp tức thì:** Hỗ trợ kéo thả 1 hoặc nhiều file cùng câu hỏi trong 1 request.
- **RAG Đa tài liệu trong cùng phiên:** Trò chuyện liên tục qua nhiều lượt (multi-turn), nạp thêm tài liệu bất cứ lúc nào.
- **Trích dẫn nguồn minh bạch:** Hiển thị rõ tên file, số trang, đoạn trích và điểm tương đồng.
- **Chống Hallucination:** Từ chối trả lời nếu tài liệu không chứa thông tin phù hợp.
