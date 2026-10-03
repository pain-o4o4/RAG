import React, { Component } from 'react';
import { connect } from 'react-redux';
import { setInspectorSource } from '../../store/actions';

class CitationInspector extends Component {
    handleClose = () => {
        this.props.dispatchSetInspectorSource(null);
    };

    render() {
        const { inspectorSource } = this.props;
        if (!inspectorSource) return null;

        const filename =
            inspectorSource.document_name ||
            inspectorSource.filename ||
            inspectorSource.source_file ||
            'Tài liệu tham chiếu';

        const page = inspectorSource.page || inspectorSource.page_number || 1;
        const chunkIndex = inspectorSource.chunk_index || 0;
        const chunkText =
            inspectorSource.content ||
            inspectorSource.text ||
            inspectorSource.chunk_content ||
            'Không có nội dung trích dẫn chi tiết.';

        const scorePercent = inspectorSource.score
            ? Math.round(inspectorSource.score * 100)
            : inspectorSource.similarity
            ? Math.round(inspectorSource.similarity * 100)
            : 95;

        return (
            <div className="citation-inspector-drawer">
                <div className="drawer-header">
                    <div className="drawer-title-group">
                        <i className="fas fa-quote-left text-info me-2" />
                        <span className="drawer-title">Chi Tiết Đoạn Trích Dẫn</span>
                    </div>
                    <button
                        type="button"
                        className="btn-close-drawer"
                        onClick={this.handleClose}
                        title="Đóng bảng trích dẫn"
                    >
                        <i className="fas fa-times" />
                    </button>
                </div>

                <div className="drawer-body">
                    {/* Document Meta Info */}
                    <div className="doc-meta-card">
                        <div className="doc-name" title={filename}>
                            <i className="far fa-file-lines me-2 text-info" />
                            {filename}
                        </div>
                        <div className="doc-tags">
                            <span className="doc-badge score">
                                <i className="fas fa-bullseye me-1" /> Độ khớp: {scorePercent}%
                            </span>
                            <span className="doc-badge page">
                                Trang {page}
                            </span>
                            <span className="doc-badge chunk">
                                Đoạn #{chunkIndex + 1}
                            </span>
                        </div>
                    </div>

                    {/* Chunk Snippet */}
                    <div className="chunk-content-section">
                        <div className="section-label">NỘI DUNG ĐOẠN TRÍCH (CHUNK SNIPPET)</div>
                        <div className="chunk-quote-box">
                            <p className="chunk-text mb-0">{chunkText}</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    inspectorSource: state.app.inspectorSource
});

const mapDispatchToProps = (dispatch) => ({
    dispatchSetInspectorSource: (source) => dispatch(setInspectorSource(source))
});

export default connect(mapStateToProps, mapDispatchToProps)(CitationInspector);
