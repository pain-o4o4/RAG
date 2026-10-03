# Hướng Dẫn Khởi Tạo Dự Án FastAPI với Uvicorn (A-Z)

Tài liệu hướng dẫn chi tiết cách thiết lập, cài đặt, cấu trúc thư mục và chạy ứng dụng **FastAPI** sử dụng **Uvicorn** (ASGI Server chuẩn) trên macOS / Linux / Windows.

---

## 1. Yêu cầu tiên quyết

- **Python**: Phiên bản `>= 3.10` (khuyến nghị `3.11` hoặc `3.12`).
- Kiểm tra phiên bản Python trên máy:
  ```bash
  python3 --version
  ```

---

## 2. Các bước khởi tạo dự án

### Bước 1: Tạo và kích hoạt môi trường ảo (Virtual Environment)

Môi trường ảo giúp cô lập các thư viện của dự án, tránh xung đột với hệ thống.

```bash
# 1. Tạo môi trường ảo có tên là .venv
python3 -m venv .venv

# 2. Kích hoạt môi trường ảo:
# Trên macOS / Linux:
source .venv/bin/activate

# Trên Windows (Command Prompt):
# .venv\Scripts\activate.bat

# Trên Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

> **Mẹo:** Khi kích hoạt thành công, đầu dòng lệnh terminal sẽ xuất hiện tiền tố `(.venv)`.

---

### Bước 2: Cài đặt FastAPI và Uvicorn

Cài đặt FastAPI cùng Uvicorn bản chuẩn đầy đủ (có kèm tối ưu C `uvloop`, `httptools`):

```bash
pip install --upgrade pip
pip install fastapi "uvicorn[standard]"
uv pip install -r requirements.txt
```

---

### Bước 3: Tạo file ứng dụng chính (`main.py`)

Tạo file `main.py` ở thư mục gốc:

```python
import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="RAG Backend API",
    description="Dự án FastAPI phục vụ hệ thống RAG & AI Agent",
    version="1.0.0"
)

@app.get("/", tags=["Health Check"])
def read_root():
    """Kiểm tra trạng thái hoạt động của server."""
    return {
        "status": "online",
        "message": "FastAPI server chạy trên Uvicorn thành công!"
    }

@app.get("/items/{item_id}", tags=["Sample"])
def read_item(item_id: int, q: str | None = None):
    """API mẫu nhận Path Parameter và Query Parameter."""
    return {"item_id": item_id, "query": q}


# Cho phép chạy trực tiếp bằng lệnh: python main.py
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

---

### Bước 4: Chạy Server với Uvicorn

Bạn có thể chạy ứng dụng bằng 1 trong 2 cách sau:

#### Cách 1: Chạy qua dòng lệnh Uvicorn CLI (Phổ biến nhất trong quá trình phát triển)

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

> **Giải thích các tham số của Uvicorn:**
>
> - `main:app`: `main` là tên file `main.py`, `app` là biến thể hiện `FastAPI()` bên trong file đó.
> - `--reload`: Tự động khởi động lại server mỗi khi bạn chỉnh sửa và lưu code (rất tiện khi dev).
> - `--host 127.0.0.1`: Lắng nghe trên localhost (hoặc dùng `0.0.0.0` nếu muốn các máy khác trong mạng nội bộ / Docker kết nối được).
> - `--port 8000`: Cổng chạy server (có thể đổi sang `8080`, `5000` tùy ý).

#### Cách 2: Chạy trực tiếp qua Python script

Nếu đã thêm đoạn `if __name__ == "__main__":` ở cuối file `main.py`, bạn chỉ cần chạy:

```bash
python main.py
```

#### Cách 3: Chạy môi trường Production (Chạy nhiều tiến trình workers)

Khi đưa lên Production/Server thực tế, không dùng `--reload` mà bật nhiều worker để tận dụng đa nhân CPU:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

### Bước 5: Kiểm tra API Documentation (Swagger & ReDoc)

Sau khi Uvicorn khởi chạy, mở trình duyệt để kiểm tra:

- **Trang chủ API:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger UI (Giao diện tương tác & test API):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Tài liệu chi tiết, chuyên nghiệp):** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### Bước 6: Đóng băng danh sách thư viện (`requirements.txt`)

Lưu lại các thư viện đã cài để chia sẻ hoặc deploy:

```bash
pip freeze > requirements.txt
```

Nội dung file `requirements.txt` tối thiểu sẽ gồm:

```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
```

Sau này khi deploy hoặc sang máy khác, chỉ cần chạy:

```bash
pip install -r requirements.txt
```

---

## 3. Cấu trúc thư mục chuẩn cho dự án lớn (RAG / AI Service)

Khi dự án mở rộng, bạn nên chia tách code thành các tầng rõ ràng:

```text
RAG/
├── app/
│   ├── __init__.py
│   ├── main.py             # Entrypoint khởi tạo FastAPI app & Uvicorn config
│   ├── core/               # Cấu hình chung, security, env
│   │   ├── __init__.py
│   │   ├── config.py       # Cấu hình Pydantic Settings
│   │   └── database.py     # Kết nối Database / Vector DB
│   ├── api/                # Định nghĩa các Route & Endpoints
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py   # Gom nhóm các sub-routers
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── chat.py     # Endpoint chat / hỏi đáp
│   │           ├── document.py # Endpoint upload & index tài liệu
│   │           └── health.py
│   ├── models/             # Định nghĩa Pydantic Schemas & ORM Models
│   │   ├── __init__.py
│   │   ├── chat_schema.py
│   │   └── doc_schema.py
│   └── services/           # Business Logic xử lý RAG & LLM
│       ├── __init__.py
│       ├── llm_service.py      # Tương tác với LLM (Gemini/OpenAI)
│       ├── embedding.py        # Vector embedding generator
│       └── retriever.py        # Tìm kiếm Vector / Hybrid Search
├── guide/                  # Tài liệu hướng dẫn dự án
│   └── begin.md
├── data/                   # Dữ liệu mẫu / file upload tạm thời
├── .env.example            # File mẫu biến môi trường
├── .env                    # Biến môi trường thực tế (API key, v.v.)
├── .gitignore              # Bỏ qua .venv, .env, __pycache__
├── requirements.txt
└── README.md
```

---

## 4. File `.gitignore` khuyến nghị

Tạo file `.gitignore` ở thư mục gốc để tránh đẩy rác lên Git:

```gitignore
# Virtual Environment
.venv/
env/
venv/
ENV/

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so

# Environment variables
.env
.env.local

# IDE & Editor
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Data & logs
data/
*.log
```
