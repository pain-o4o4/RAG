import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
    fetchDocuments,
    uploadDocumentsBatch,
    deleteDocument,
    createNewSession
} from '../../store/actions/ragActions';
import { setActiveTab } from '../../store/actions';

class DocumentManager extends Component {
    fileInputRef = React.createRef();

    componentDidMount() {
        this.props.dispatchFetchDocuments();
    }

    handleFileInputChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            this.props.dispatchUploadDocuments(Array.from(e.target.files));
        }
    };

    handleDelete = (doc) => {
        if (window.confirm(`Xóa tài liệu "${doc.filename || doc.name}" khỏi thư viện?`)) {
            this.props.dispatchDeleteDocument(doc.id);
        }
    };

    handleChatWithDoc = (doc) => {
        const title = `Hỏi đáp: ${doc.filename || doc.name}`;
        this.props.dispatchCreateSession(title, doc.id);
        this.props.dispatchSetActiveTab('chat');
    };

    formatFileSize = (bytes) => {
        if (!bytes) return '0 KB';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    render() {
        const { documents, isUploading, isLoadingDocuments } = this.props;

        return (
            <div className="grok-subview-container">
                <div className="subview-header">
                    <div>
                        <h2 className="title">Thư Viện Tài Liệu & Kho Tri Thức</h2>
                        <p className="subtitle">
                            Quản lý các tài liệu đã nạp vào RAG Pipeline. Hệ thống tự động chia đoạn (chunks) và sinh Embeddings để tra cứu chính xác.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm rounded-pill px-3"
                        onClick={() => this.props.dispatchFetchDocuments()}
                    >
                        <i className={`fas fa-sync-alt ${isLoadingDocuments ? 'fa-spin' : ''} me-1`} />
                        Làm mới
                    </button>
                </div>

                {/* Dropzone Card */}
                <div
                    className="grok-dropzone"
                    onClick={() => this.fileInputRef.current && this.fileInputRef.current.click()}
                >
                    <input
                        ref={this.fileInputRef}
                        type="file"
                        multiple
                        className="d-none"
                        onChange={this.handleFileInputChange}
                        accept=".pdf,.docx,.doc,.txt,.md,.csv"
                    />
                    <div className="icon-wrap">
                        <i className={`fas ${isUploading ? 'fa-spinner fa-spin' : 'fa-cloud-arrow-up'}`} />
                    </div>
                    <div className="heading">
                        {isUploading ? 'Đang tải lên và vector hóa...' : 'Kéo thả tệp vào đây hoặc nhấp để tải lên thư viện'}
                    </div>
                    <div className="hint">
                        Hỗ trợ định dạng: PDF, DOCX, TXT, Markdown (.md), CSV
                    </div>
                </div>

                {/* Documents Grid */}
                <div className="docs-grid">
                    {(documents || []).map((doc) => {
                        const filename = doc.filename || doc.name || 'Tài liệu không tên';
                        const chunkCount = doc.chunks_count || doc.chunk_count || 1;
                        const fileSize = this.formatFileSize(doc.file_size || doc.size);
                        const status = doc.status || 'COMPLETED';

                        return (
                            <div key={doc.id} className="doc-card">
                                <div className="card-top">
                                    <i className="far fa-file-lines icon" />
                                    <span className="status-badge">{status}</span>
                                </div>
                                <h4 className="doc-title" title={filename}>
                                    {filename}
                                </h4>
                                <div className="doc-info">
                                    <span>{fileSize}</span>
                                    <span>•</span>
                                    <span>{chunkCount} chunks</span>
                                </div>
                                <div className="card-bottom-actions">
                                    <button
                                        type="button"
                                        className="btn-ask"
                                        onClick={() => this.handleChatWithDoc(doc)}
                                    >
                                        <i className="far fa-comment-dots me-1" /> Hỏi đáp
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-trash"
                                        onClick={() => this.handleDelete(doc)}
                                        title="Xóa tài liệu"
                                    >
                                        <i className="far fa-trash-can" />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    documents: state.rag.documents,
    isUploading: state.rag.isUploading,
    isLoadingDocuments: state.rag.isLoadingDocuments
});

const mapDispatchToProps = (dispatch) => ({
    dispatchFetchDocuments: () => dispatch(fetchDocuments()),
    dispatchUploadDocuments: (files) => dispatch(uploadDocumentsBatch(files)),
    dispatchDeleteDocument: (id) => dispatch(deleteDocument(id)),
    dispatchCreateSession: (title, docId) => dispatch(createNewSession(title, docId)),
    dispatchSetActiveTab: (tab) => dispatch(setActiveTab(tab))
});

export default connect(mapStateToProps, mapDispatchToProps)(DocumentManager);
