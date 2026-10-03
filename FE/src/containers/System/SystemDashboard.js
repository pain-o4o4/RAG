import React, { Component } from 'react';
import { connect } from 'react-redux';
import { checkBackendHealth } from '../../store/actions';
import { fetchDocuments, fetchChatSessions } from '../../store/actions/ragActions';

class SystemDashboard extends Component {
    componentDidMount() {
        this.props.dispatchCheckHealth();
        this.props.dispatchFetchDocuments();
        this.props.dispatchFetchSessions();
    }

    render() {
        const { backendHealth, totalDocuments, documents, sessions } = this.props;
        const isOnline = backendHealth?.status === 'ok' || backendHealth?.status === 'healthy';
        const docCount = totalDocuments || (documents ? documents.length : 0);
        const sessionCount = sessions ? sessions.length : 0;

        return (
            <div className="grok-subview-container">
                <div className="subview-header">
                    <div>
                        <h2 className="title">Tự Động Hóa & Hệ Thống RAG Pipeline</h2>
                        <p className="subtitle">
                            Theo dõi trạng thái dịch vụ FastAPI, mô hình Embeddings, Vector Store và cấu hình sinh câu trả lời.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm rounded-pill px-3"
                        onClick={this.props.dispatchCheckHealth}
                    >
                        <i className="fas fa-arrows-rotate me-1" /> Kiểm tra kết nối
                    </button>
                </div>

                {/* Metrics */}
                <div className="system-metrics-grid">
                    <div className="metric-tile">
                        <span className="label">FastAPI Backend</span>
                        <span className="val" style={{ color: isOnline ? '#22c55e' : '#ef4444' }}>
                            {isOnline ? 'ONLINE' : 'OFFLINE'}
                        </span>
                        <span className="text-muted small">127.0.0.1:8000</span>
                    </div>

                    <div className="metric-tile">
                        <span className="label">Tài Liệu Đã Nạp</span>
                        <span className="val">{docCount} Files</span>
                        <span className="text-muted small">Đã vector hóa vào FAISS</span>
                    </div>

                    <div className="metric-tile">
                        <span className="label">Phiên Hội Thoại</span>
                        <span className="val">{sessionCount} Sessions</span>
                        <span className="text-muted small">Lưu trữ lịch sử ngữ cảnh</span>
                    </div>
                </div>

                {/* Architecture Steps */}
                <div className="docs-grid mt-2">
                    <div className="doc-card">
                        <div className="card-top">
                            <span className="text-muted fw-bold">Bước 1</span>
                            <span className="status-badge">Parser</span>
                        </div>
                        <h4 className="doc-title">Document Extraction</h4>
                        <p className="text-muted small mb-0">
                            Trích xuất PDF/DOCX/TXT và chia đoạn bằng RecursiveCharacterTextSplitter.
                        </p>
                    </div>

                    <div className="doc-card">
                        <div className="card-top">
                            <span className="text-muted fw-bold">Bước 2</span>
                            <span className="status-badge">Embeddings</span>
                        </div>
                        <h4 className="doc-title">Gemini Text Embedding</h4>
                        <p className="text-muted small mb-0">
                            Vector hóa ngữ nghĩa 768 chiều với text-embedding-004.
                        </p>
                    </div>

                    <div className="doc-card">
                        <div className="card-top">
                            <span className="text-muted fw-bold">Bước 3</span>
                            <span className="status-badge">Vector DB</span>
                        </div>
                        <h4 className="doc-title">FAISS Vector Search</h4>
                        <p className="text-muted small mb-0">
                            Truy vấn tương đồng Cosine Similarity để lấy các đoạn văn bản phù hợp nhất.
                        </p>
                    </div>

                    <div className="doc-card">
                        <div className="card-top">
                            <span className="text-muted fw-bold">Bước 4</span>
                            <span className="status-badge">Generation</span>
                        </div>
                        <h4 className="doc-title">Gemini 2.5 LLM</h4>
                        <p className="text-muted small mb-0">
                            Sinh câu trả lời mạch lạc dựa trên tài liệu kèm trích dẫn nguồn.
                        </p>
                    </div>
                </div>

                {/* OpenAPI link */}
                <div className="doc-card mt-2">
                    <div className="d-flex justify-content-between align-items-center">
                        <div>
                            <h4 className="doc-title mb-1">Tài Liệu OpenAPI / Swagger Backend</h4>
                            <p className="text-muted small mb-0">Xem toàn bộ schema dữ liệu và test API endpoints trực tiếp.</p>
                        </div>
                        <a
                            href="http://127.0.0.1:8000/docs"
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline-light btn-sm rounded-pill px-3"
                        >
                            <i className="fas fa-external-link-alt me-1" /> Mở Swagger UI
                        </a>
                    </div>
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    backendHealth: state.app.backendHealth,
    totalDocuments: state.rag.totalDocuments,
    documents: state.rag.documents,
    sessions: state.rag.sessions
});

const mapDispatchToProps = (dispatch) => ({
    dispatchCheckHealth: () => dispatch(checkBackendHealth()),
    dispatchFetchDocuments: () => dispatch(fetchDocuments()),
    dispatchFetchSessions: () => dispatch(fetchChatSessions())
});

export default connect(mapStateToProps, mapDispatchToProps)(SystemDashboard);
