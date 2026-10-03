# RAG Backend API

Hệ thống RAG (Retrieval-Augmented Generation) & AI Agent Backend xây dựng trên nền tảng **FastAPI**, **SQLAlchemy (Async)**, **Google Gemini GenAI**, và **Vector Search (FAISS)**.

---

## 🛠️ Yêu cầu môi trường
- Python >= 3.10 (Khuyến nghị 3.11 hoặc 3.12)
- Virtual environment (`.venv`)

---

## 🚀 Hướng dẫn cài đặt & khởi chạy

### 1. Khởi tạo môi trường ảo
```bash
python3 -m venv .venv
source .venv/bin/activate  # Trên macOS / Linux
```

### 2. Cài đặt thư viện
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Sao chép `.env.example` thành `.env` và điền thông tin:
```bash
cp .env.example .env
```

### 4. Khởi chạy Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Truy cập API Documentation
- **Swagger UI:** [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
- **ReDoc:** [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
