# HỆ THỐNG TÀI LIỆU DỰ ÁN FASTAPI RAG SYSTEM

Thư mục `docs/` chứa toàn bộ tài liệu đặc tả nghiệp vụ và kiến trúc kỹ thuật của hệ thống:

---

## 📑 DANH MỤC TÀI LIỆU

1. **[01_BA_REQUIREMENTS_SPECIFICATION.md](file:///Users/pain.o4o4/Documents/fastAPI/docs/01_BA_REQUIREMENTS_SPECIFICATION.md)**
   - Đặc tả yêu cầu nghiệp vụ (Business Requirements Document - BRD/BA).
   - Phân tích Tác nhân (Actors), Sơ đồ Use Case & Chi tiết từng Use Case.
   - Sơ đồ quy trình nghiệp vụ (Activity & Sequence Diagram bằng Mermaid).
   - Quy tắc nghiệp vụ (Business Rules) & Chống Hallucination.
   - Thiết kế Cơ sở dữ liệu (ERD) & Đặc tả API Contracts.
   - Tiêu chí nghiệm thu (Acceptance Criteria).

2. **[02_ARCHITECTURE_AND_CODEBASE_GUIDE.md](file:///Users/pain.o4o4/Documents/fastAPI/docs/02_ARCHITECTURE_AND_CODEBASE_GUIDE.md)**
   - Sơ đồ cấu trúc thư mục chuẩn và trách nhiệm của từng module.
   - Hướng dẫn chi tiết đường dẫn code và giải thích hoạt động của từng file:
     - Tầng Cấu hình & Hạ tầng (`app/core/`)
     - Tầng Cơ sở dữ liệu ORM (`app/models/`)
     - Tầng Validation Request/Response (`app/schemas/`)
     - Tầng Xử lý RAG Pipeline (`app/services/`)
     - Tầng Điều khiển API (`app/routers/`)
     - Entrypoint khởi chạy (`app/main.py`)
   - Hướng dẫn cài đặt, khởi chạy và các kịch bản kiểm thử (cURL / Swagger UI).
