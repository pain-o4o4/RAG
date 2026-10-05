from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings


class GeminiEmbeddings(GoogleGenerativeAIEmbeddings):
    """
    Embedding Service chuẩn LangChain sử dụng Google Gemini Embeddings:
    - Kế thừa trực tiếp GoogleGenerativeAIEmbeddings của LangChain.
    - Tự động nạp model và API key từ cấu hình hệ thống.
    - Tương thích 100% với FAISS VectorStore.
    """

    def __init__(self, **kwargs):
        model_name = settings.EMBEDDING_MODEL
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        super().__init__(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            **kwargs
        )


# Alias tương thích ngược
GeminiEmbeddings768 = GeminiEmbeddings
