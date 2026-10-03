import React, { Component } from 'react';
import { connect } from 'react-redux';
import { setActiveTab } from '../../store/actions';
import { sendMessage, createNewSession } from '../../store/actions/ragActions';

class ImagineStudio extends Component {
    state = {
        prompt: '',
        isGenerating: false,
        gallery: [
            {
                id: 1,
                title: 'Trực quan hóa Kiến Trúc RAG Pipeline',
                desc: 'Sơ đồ luồng xử lý Embeddings & Vector Search',
                tag: 'Kiến trúc hệ thống'
            },
            {
                id: 2,
                title: 'Tóm tắt Tri thức Đa chiều',
                desc: 'Phân tích liên kết giữa các tài liệu PDF nội bộ',
                tag: 'Document Graph'
            },
            {
                id: 3,
                title: 'Báo cáo Phân tích Tài liệu',
                desc: 'Tổng hợp dữ liệu trích xuất từ các bảng và biểu đồ',
                tag: 'Báo cáo thông minh'
            }
        ]
    };

    handleExplore = (item) => {
        this.props.dispatchCreateNewSession(item.title);
        this.props.dispatchSetActiveTab('chat');
        setTimeout(() => {
            this.props.dispatchSendMessage(this.props.activeSessionId, `Hãy giải thích chi tiết về: ${item.title}`);
        }, 300);
    };

    render() {
        const { gallery } = this.state;

        return (
            <div className="grok-subview-container">
                <div className="subview-header">
                    <div>
                        <h2 className="title">Imagine Studio & Sáng Tạo</h2>
                        <p className="subtitle">
                            Khám phá và trực quan hóa các khái niệm, sơ đồ tri thức và tổng hợp đa phương tiện từ kho dữ liệu RAG.
                        </p>
                    </div>
                </div>

                <div className="docs-grid">
                    {gallery.map((item) => (
                        <div key={item.id} className="doc-card">
                            <div className="card-top">
                                <i className="fas fa-wand-magic-sparkles text-cyan fs-4" />
                                <span className="status-badge">{item.tag}</span>
                            </div>
                            <h4 className="doc-title">{item.title}</h4>
                            <p className="text-muted small mb-0">{item.desc}</p>
                            <div className="card-bottom-actions">
                                <button
                                    type="button"
                                    className="btn-ask w-100"
                                    onClick={() => this.handleExplore(item)}
                                >
                                    <i className="fas fa-sparkles me-1" /> Khám phá với AI
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    activeSessionId: state.rag.activeSessionId
});

const mapDispatchToProps = (dispatch) => ({
    dispatchSetActiveTab: (tab) => dispatch(setActiveTab(tab)),
    dispatchCreateNewSession: (title) => dispatch(createNewSession(title)),
    dispatchSendMessage: (id, content) => dispatch(sendMessage(id, content))
});

export default connect(mapStateToProps, mapDispatchToProps)(ImagineStudio);
