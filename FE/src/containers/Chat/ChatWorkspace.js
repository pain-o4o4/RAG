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
import MarkdownIt from 'markdown-it';

const mdParser = new MarkdownIt({ breaks: true, linkify: true });

const renderMarkdownContent = (content) => {
    if (!content) return '';

    // Normalize markdown content:
    // 1. Convert unicode bullets (•, ●, ○) to standard markdown list syntax '- '
    // 2. Collapse blank lines between consecutive list items so it renders as a tight list (no <p> inside <li>)
    const lines = content.split('\n');
    const processed = [];

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        const trimmed = line.trim();
        const isBullet = /^[•●○]\s*/.test(trimmed);
        if (isBullet) {
            line = line.replace(/^[ \t]*[•●○]\s*/, '- ');
        }

        if (trimmed === '') {
            let nextNonEmpty = '';
            for (let j = i + 1; j < lines.length; j++) {
                if (lines[j].trim() !== '') {
                    nextNonEmpty = lines[j].trim();
                    break;
                }
            }
            const nextIsListItem = /^[•●○]\s*/.test(nextNonEmpty) || /^[-*+]\s+/.test(nextNonEmpty) || /^\d+\.\s+/.test(nextNonEmpty);

            let prevNonEmpty = '';
            for (let k = processed.length - 1; k >= 0; k--) {
                if (processed[k].trim() !== '') {
                    prevNonEmpty = processed[k].trim();
                    break;
                }
            }
            const prevIsListItem = /^[-*+]\s+/.test(prevNonEmpty) || /^\d+\.\s+/.test(prevNonEmpty) || /^[•●○]\s*/.test(prevNonEmpty);

            if (prevIsListItem && nextIsListItem) {
                continue; // Skip the blank line to keep list items compact!
            }
        }

        processed.push(line);
    }

    let html = mdParser.render(processed.join('\n'));
    // Strip loose <p> tags inside <li> to prevent Bootstrap paragraph spacing
    html = html.replace(/<li>\s*<p>([\s\S]*?)<\/p>\s*<\/li>/gi, '<li>$1</li>');
    return html;
};

class ChatWorkspace extends Component {
    state = {
        inputValue: '',
        attachedFiles: [],
        isDragging: false,
        thinkingSeconds: 0
    };

    messagesEndRef = React.createRef();
    inputRef = React.createRef();
    fileInputRef = React.createRef();
    thinkingInterval = null;

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
            if (!this.props.isSendingMessage) {
                this.props.dispatchFetchMessages(this.props.activeSessionId);
            }
        }
        if (prevProps.messages?.length !== this.props.messages?.length || this.props.isSendingMessage) {
            this.scrollToBottom();
        }

        const isNowBusy = this.props.isSendingMessage || this.props.isUploading;
        const wasBusy = prevProps.isSendingMessage || prevProps.isUploading;

        if (isNowBusy && !wasBusy) {
            this.setState({ thinkingSeconds: 0 });
            if (this.thinkingInterval) clearInterval(this.thinkingInterval);
            this.thinkingInterval = setInterval(() => {
                this.setState((prev) => ({ thinkingSeconds: prev.thinkingSeconds + 1 }));
            }, 1000);
        } else if (!isNowBusy && wasBusy) {
            if (this.thinkingInterval) {
                clearInterval(this.thinkingInterval);
                this.thinkingInterval = null;
            }
        }
    }

    componentWillUnmount() {
        if (this.thinkingInterval) {
            clearInterval(this.thinkingInterval);
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
        const { activeSessionId } = this.props;

        if (!inputValue.trim() && attachedFiles.length === 0) return;

        const messageText = inputValue.trim();
        const filesToUpload = [...attachedFiles];

        // Clear input and files immediately for smooth UX
        this.setState({
            inputValue: '',
            attachedFiles: []
        });

        // Send message with attached files directly in one unified request
        await this.props.dispatchSendMessage(activeSessionId, messageText, filesToUpload);
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
        const { messages, activeSessionId, isLoadingMessages, isSendingMessage, isUploading } = this.props;
        const { isDragging } = this.state;
        const hasMessages = messages && messages.length > 0;
        const showStream = Boolean(activeSessionId || hasMessages || isSendingMessage || isUploading);

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
                {!showStream ? (
                    <div className="chat-hero-screen">
                        <div className="hero-content-box">
                            <div className="hero-icon-badge">
                                <img
                                    src={`${process.env.PUBLIC_URL}/robot.png`}
                                    alt="Robot AI Assistant"
                                    className="hero-robot-img"
                                />
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
                            {isLoadingMessages && !hasMessages && (
                                <div className="chat-status-notice">
                                    <i className="fas fa-spinner fa-spin me-2 text-info" />
                                    <span>Đang tải lịch sử tin nhắn...</span>
                                </div>
                            )}

                            {!isLoadingMessages && !hasMessages && !isSendingMessage && !isUploading && (
                                <div className="chat-status-notice text-muted">
                                    <i className="far fa-message me-2" />
                                    <span>Phiên trò chuyện này chưa có câu hỏi. Nhập câu hỏi bên dưới để bắt đầu.</span>
                                </div>
                            )}
                            {messages.map((msg, index) => {
                                const isUser = msg.role === 'user';
                                const attachedDocs = isUser
                                    ? (Array.isArray(msg.files) && msg.files.length > 0
                                        ? msg.files
                                        : (Array.isArray(msg.sources) ? msg.sources : []))
                                    : [];
                                const sources = !isUser ? (msg.sources || msg.citations || []) : [];

                                if (isUser) {
                                    return (
                                        <div
                                            key={msg.id || index}
                                            className="chat-row-item user-align"
                                        >
                                            <div className="user-message-container">
                                                {/* Attached Document Pill(s) */}
                                                {attachedDocs.length > 0 && (
                                                    <div className="user-attached-docs-tray">
                                                        {attachedDocs.map((doc, dIdx) => {
                                                            const fileName = doc.filename || doc.name || 'Tài liệu đính kèm';
                                                            return (
                                                                <div key={dIdx} className="user-doc-pill" title={fileName}>
                                                                    <span className="doc-pill-icon-box">
                                                                        <i className="far fa-file-lines" />
                                                                    </span>
                                                                    <span className="doc-pill-name">{fileName}</span>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                )}

                                                {/* User Text Bubble */}
                                                {msg.content && msg.content.trim() && (
                                                    <div className="message-bubble-box user-bubble">
                                                        <div 
                                                            className="message-text-content" 
                                                            dangerouslySetInnerHTML={{ __html: renderMarkdownContent(msg.content) }} 
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                }

                                return (
                                    <div
                                        key={msg.id || index}
                                        className="chat-row-item assistant-align"
                                    >
                                        <div className="message-bubble-box assistant-bubble">
                                            <div 
                                                className="message-text-content" 
                                                dangerouslySetInnerHTML={{ __html: renderMarkdownContent(msg.content || '') }} 
                                            />

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
                                    <div className="assistant-thinking-badge">
                                        <span className="wand-icon">🪄</span>
                                        <span className="thinking-text-label">
                                            {isUploading
                                                ? 'Đang nạp và phân tích tài liệu...'
                                                : (this.state.thinkingSeconds > 0
                                                    ? `Làm việc cho ${this.state.thinkingSeconds}s`
                                                    : 'Làm việc...')}
                                        </span>
                                    </div>
                                </div>
                            )}

                            <div ref={this.messagesEndRef} />
                        </div>
                    </div>
                )}

                {/* Sticky Bottom Dock when conversation is active */}
                {showStream && (
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
    isLoadingMessages: state.rag.isLoadingMessages,
    isSendingMessage: state.rag.isSendingMessage,
    isUploading: state.rag.isUploading
});

const mapDispatchToProps = (dispatch) => ({
    dispatchFetchMessages: (id) => dispatch(fetchChatMessages(id)),
    dispatchSendMessage: (id, content, files) => dispatch(sendMessage(id, content, files)),
    dispatchCreateNewSession: (title) => dispatch(createNewSession(title)),
    dispatchUploadDocuments: (files) => dispatch(uploadDocumentsBatch(files)),
    dispatchSetInspectorSource: (src) => dispatch(setInspectorSource(src))
});

export default connect(mapStateToProps, mapDispatchToProps)(ChatWorkspace);
