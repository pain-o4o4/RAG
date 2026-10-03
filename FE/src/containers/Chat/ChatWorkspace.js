import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
    fetchChatMessages,
    sendMessage,
    createNewSession,
    uploadDocumentsBatch
} from '../../store/actions/ragActions';
import { setInspectorSource } from '../../store/actions';
import { ToastUtil } from '../../utils/ToastUtil';

class ChatWorkspace extends Component {
    state = {
        inputValue: '',
        attachedFiles: [],
        isDragging: false
    };

    messagesEndRef = React.createRef();
    inputRef = React.createRef();
    fileInputRef = React.createRef();

    componentDidMount() {
        const { activeSessionId } = this.props;
        if (activeSessionId) {
            this.props.dispatchFetchMessages(activeSessionId);
        }
        if (this.inputRef.current) {
            this.inputRef.current.focus();
        }
    }

    componentDidUpdate(prevProps) {
        if (prevProps.activeSessionId !== this.props.activeSessionId && this.props.activeSessionId) {
            this.props.dispatchFetchMessages(this.props.activeSessionId);
        }
        if (prevProps.messages?.length !== this.props.messages?.length || this.props.isSendingMessage) {
            this.scrollToBottom();
        }
    }

    scrollToBottom = () => {
        if (this.messagesEndRef.current) {
            this.messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    };

    handleInputChange = (e) => {
        this.setState({ inputValue: e.target.value });
    };

    handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSend();
        }
    };

    handleAttachClick = () => {
        if (this.fileInputRef.current) {
            this.fileInputRef.current.click();
        }
    };

    handleFileInputChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            this.addFiles(Array.from(e.target.files));
            if (this.fileInputRef.current) {
                this.fileInputRef.current.value = '';
            }
        }
    };

    addFiles = (newFiles) => {
        const validExtensions = ['.pdf', '.txt', '.docx', '.doc', '.md', '.csv', '.json'];
        const filtered = newFiles.filter((f) => {
            const ext = '.' + f.name.split('.').pop().toLowerCase();
            return validExtensions.includes(ext);
        });

        if (filtered.length === 0) {
            ToastUtil.warn('Vui lòng chọn định dạng tệp hợp lệ (.pdf, .docx, .txt, .md, .csv)');
            return;
        }

        this.setState((prev) => {
            const existingNames = new Set(prev.attachedFiles.map((file) => file.name));
            const uniqueNew = filtered.filter((file) => !existingNames.has(file.name));
            return {
                attachedFiles: [...prev.attachedFiles, ...uniqueNew]
            };
        });
    };

    handleRemoveFile = (index) => {
        this.setState((prev) => ({
            attachedFiles: prev.attachedFiles.filter((_, idx) => idx !== index)
        }));
    };

    handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!this.state.isDragging) {
            this.setState({ isDragging: true });
        }
    };

    handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.setState({ isDragging: false });
    };

    handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.setState({ isDragging: false });

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            this.addFiles(Array.from(e.dataTransfer.files));
        }
    };

    formatFileSize = (bytes) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    getFileIcon = (filename) => {
        const ext = (filename || '').split('.').pop().toLowerCase();
        switch (ext) {
            case 'pdf': return 'fa-file-pdf text-danger';
            case 'docx':
            case 'doc': return 'fa-file-word text-primary';
            case 'txt': return 'fa-file-lines text-secondary';
            case 'md': return 'fa-file-code text-info';
            case 'csv': return 'fa-file-excel text-success';
            default: return 'fa-file text-muted';
        }
    };

    handleQuickPrompt = (promptText) => {
        this.setState({ inputValue: promptText }, () => {
            this.handleSend();
        });
    };

    handleSend = async () => {
        const { inputValue, attachedFiles } = this.state;
        let { activeSessionId } = this.props;

        if (!inputValue.trim() && attachedFiles.length === 0) return;

        const messageText = inputValue.trim() || 'Hãy tóm tắt và phân tích các tài liệu tôi đính kèm.';
        const filesToUpload = [...attachedFiles];

        // Clear input and files immediately for smooth UX
        this.setState({
            inputValue: '',
            attachedFiles: []
        });

        // Ensure an active session exists
        if (!activeSessionId) {
            const previewTitle = messageText.length > 25 ? messageText.substring(0, 25) + '...' : messageText;
            const newSession = await this.props.dispatchCreateNewSession(previewTitle);
            if (newSession && newSession.id) {
                activeSessionId = newSession.id;
            } else {
                ToastUtil.error('Không thể tạo phiên trò chuyện.');
                return;
            }
        }

        // Upload attached files if any
        if (filesToUpload.length > 0) {
            await this.props.dispatchUploadDocuments(filesToUpload);
        }

        // Send message to RAG session
        await this.props.dispatchSendMessage(activeSessionId, messageText);
    };

    renderInputCard = () => {
        const { inputValue, attachedFiles } = this.state;
        const { isSendingMessage, isUploading } = this.props;
        const isBusy = isSendingMessage || isUploading;

        return (
            <div className="chat-input-box-wrapper">
                {/* Hidden File Input */}
                <input
                    ref={this.fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.doc,.txt,.md,.csv,.json"
                    className="d-none"
                    onChange={this.handleFileInputChange}
                    disabled={isBusy}
                />

                {/* Attached Files Chips Tray */}
                {attachedFiles.length > 0 && (
                    <div className="attached-files-tray">
                        {attachedFiles.map((file, idx) => (
                            <div key={idx} className="file-chip-item">
                                <i className={`fas ${this.getFileIcon(file.name)} me-1`} />
                                <span className="file-chip-name" title={file.name}>
                                    {file.name}
                                </span>
                                <span className="file-chip-size">
                                    ({this.formatFileSize(file.size)})
                                </span>
                                <button
                                    type="button"
                                    className="btn-remove-chip"
                                    onClick={() => this.handleRemoveFile(idx)}
                                    title="Xóa tệp đính kèm"
                                >
                                    <i className="fas fa-times" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Textarea and Action Buttons */}
                <div className="input-row-container">
                    <button
                        type="button"
                        className="btn-attach-action"
                        onClick={this.handleAttachClick}
                        disabled={isBusy}
                        title="Đính kèm tài liệu (PDF, DOCX, TXT, CSV...)"
                    >
                        <i className="fas fa-paperclip" />
                    </button>

                    <textarea
                        ref={this.inputRef}
                        className="chat-main-textarea"
                        rows={1}
                        placeholder={
                            attachedFiles.length > 0
                                ? `Đã đính kèm ${attachedFiles.length} tệp. Nhập câu hỏi hoặc nhấn Gửi...`
                                : 'Hỏi bất kỳ điều gì hoặc đính kèm tài liệu...'
                        }
                        value={inputValue}
                        onChange={this.handleInputChange}
                        onKeyDown={this.handleKeyDown}
                        disabled={isBusy}
                    />

                    <button
                        type="button"
                        className={`btn-send-message ${inputValue.trim() || attachedFiles.length > 0 ? 'active' : ''}`}
                        onClick={this.handleSend}
                        disabled={(!inputValue.trim() && attachedFiles.length === 0) || isBusy}
                        title="Gửi câu hỏi"
                    >
                        <i className={`fas ${isBusy ? 'fa-spinner fa-spin' : 'fa-arrow-up'}`} />
                    </button>
                </div>
            </div>
        );
    };

    render() {
        const { messages, isSendingMessage, isUploading } = this.props;
        const { isDragging } = this.state;
        const hasMessages = messages && messages.length > 0;

        const quickPrompts = [
            {
                icon: 'fa-file-lines',
                title: 'Tóm tắt tài liệu',
                prompt: 'Hãy tóm tắt nội dung chính và các điểm cần lưu ý từ các tài liệu được cung cấp.'
            },
            {
                icon: 'fa-magnifying-glass',
                title: 'Tra cứu thông tin',
                prompt: 'Tìm kiếm các quy định, điều khoản hoặc thông số quan trọng trong kho tri thức.'
            },
            {
                icon: 'fa-list-check',
                title: 'Trích xuất yêu cầu',
                prompt: 'Liệt kê danh sách các yêu cầu kỹ thuật và điều kiện cần tuân thủ.'
            },
            {
                icon: 'fa-brain',
                title: 'Đối chiếu và phân tích',
                prompt: 'So sánh sự khác biệt và tổng hợp dữ liệu từ các văn bản.'
            }
        ];

        return (
            <div
                className={`chat-workspace-canvas ${isDragging ? 'dragging-over' : ''}`}
                onDragOver={this.handleDragOver}
                onDragLeave={this.handleDragLeave}
                onDrop={this.handleDrop}
            >
                {/* Drag Overlay Notice */}
                {isDragging && (
                    <div className="drag-drop-overlay">
                        <div className="drag-drop-box">
                            <i className="fas fa-cloud-arrow-up mb-2 fs-1 text-info" />
                            <h4>Thả tệp vào đây để đính kèm</h4>
                            <p className="text-muted small">Hỗ trợ PDF, DOCX, TXT, Markdown, CSV</p>
                        </div>
                    </div>
                )}

                {/* Empty State: Center Hero Screen */}
                {!hasMessages ? (
                    <div className="chat-hero-screen">
                        <div className="hero-content-box">
                            <div className="hero-icon-badge">
                                <i className="fas fa-sparkles" />
                            </div>
                            <h1 className="hero-main-title">Tôi có thể giúp gì cho bạn hôm nay?</h1>
                            <p className="hero-sub-title">
                                Đính kèm tài liệu từ nút kẹp giấy (📎) hoặc đặt câu hỏi để RAG AI tra cứu và trả lời chính xác.
                            </p>

                            <div className="hero-input-area">
                                {this.renderInputCard()}
                            </div>

                            {/* Quick Suggestion Pills */}
                            <div className="quick-prompts-grid">
                                {quickPrompts.map((item, idx) => (
                                    <div
                                        key={idx}
                                        className="quick-prompt-card"
                                        onClick={() => this.handleQuickPrompt(item.prompt)}
                                    >
                                        <div className="prompt-card-icon">
                                            <i className={`fas ${item.icon}`} />
                                        </div>
                                        <div className="prompt-card-text">
                                            <div className="title">{item.title}</div>
                                            <div className="desc">{item.prompt}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Active Conversation Message Stream */
                    <div className="chat-stream-container">
                        <div className="stream-message-column">
                            {messages.map((msg, index) => {
                                const isUser = msg.role === 'user';
                                const sources = msg.sources || msg.citations || [];

                                return (
                                    <div
                                        key={msg.id || index}
                                        className={`chat-row-item ${isUser ? 'user-align' : 'assistant-align'}`}
                                    >
                                        {!isUser && (
                                            <div className="assistant-avatar-pill">
                                                <i className="fas fa-sparkles" />
                                            </div>
                                        )}

                                        <div className="message-bubble-box">
                                            <div className="message-text-content">
                                                {msg.content}
                                            </div>

                                            {/* Citation Sources */}
                                            {sources.length > 0 && (
                                                <div className="message-citations-tray">
                                                    <div className="citations-header">
                                                        <i className="fas fa-bookmark me-1" />
                                                        Nguồn trích dẫn ({sources.length}):
                                                    </div>
                                                    <div className="citation-chips-group">
                                                        {sources.map((src, sIdx) => {
                                                            const docName =
                                                                src.document_name ||
                                                                src.filename ||
                                                                `Nguồn #${sIdx + 1}`;
                                                            const pageNum = src.page || src.page_number || 1;

                                                            return (
                                                                <button
                                                                    key={sIdx}
                                                                    type="button"
                                                                    className="citation-source-chip"
                                                                    onClick={() => this.props.dispatchSetInspectorSource(src)}
                                                                    title="Nhấp để xem chi tiết đoạn trích dẫn"
                                                                >
                                                                    <i className="far fa-file-lines me-1 text-info" />
                                                                    <span className="source-doc-name">{docName}</span>
                                                                    <span className="source-page-tag">p.{pageNum}</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}

                            {/* Thinking & Retrieval Indicator */}
                            {(isSendingMessage || isUploading) && (
                                <div className="chat-row-item assistant-align">
                                    <div className="assistant-avatar-pill">
                                        <i className="fas fa-sparkles" />
                                    </div>
                                    <div className="thinking-bubble-box">
                                        <div className="pulse-dots-loader">
                                            <span />
                                            <span />
                                            <span />
                                        </div>
                                        <span className="thinking-text-label">
                                            {isUploading ? 'Đang vector hóa tài liệu đính kèm...' : 'RAG AI đang tra cứu và tổng hợp câu trả lời...'}
                                        </span>
                                    </div>
                                </div>
                            )}

                            <div ref={this.messagesEndRef} />
                        </div>
                    </div>
                )}

                {/* Sticky Bottom Dock when conversation is active */}
                {hasMessages && (
                    <div className="sticky-bottom-dock">
                        <div className="dock-column-inner">
                            {this.renderInputCard()}
                        </div>
                    </div>
                )}
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    activeSessionId: state.rag.activeSessionId,
    messages: state.rag.messages,
    isSendingMessage: state.rag.isSendingMessage,
    isUploading: state.rag.isUploading
});

const mapDispatchToProps = (dispatch) => ({
    dispatchFetchMessages: (id) => dispatch(fetchChatMessages(id)),
    dispatchSendMessage: (id, content) => dispatch(sendMessage(id, content)),
    dispatchCreateNewSession: (title) => dispatch(createNewSession(title)),
    dispatchUploadDocuments: (files) => dispatch(uploadDocumentsBatch(files)),
    dispatchSetInspectorSource: (src) => dispatch(setInspectorSource(src))
});

export default connect(mapStateToProps, mapDispatchToProps)(ChatWorkspace);
