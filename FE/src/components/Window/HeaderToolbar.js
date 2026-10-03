import React, { Component } from 'react';
import { connect } from 'react-redux';
import { setActiveTab, toggleSidebar, checkBackendHealth } from '../../store/actions';
import { createNewSession } from '../../store/actions/ragActions';

class HeaderToolbar extends Component {
    componentDidMount() {
        this.props.dispatchCheckHealth();
    }

    handleTabChange = (tabKey) => {
        this.props.dispatchSetActiveTab(tabKey);
    };

    handleNewChat = () => {
        this.props.dispatchSetActiveTab('chat');
        this.props.dispatchCreateNewSession('Cuộc trò chuyện mới');
    };

    render() {
        const { activeTab, isSidebarOpen, backendHealth } = this.props;
        const isOnline = backendHealth?.status === 'ok' || backendHealth?.status === 'healthy';

        return (
            <header className="app-topbar">
                {/* Left side: Window Controls & Sidebar toggle */}
                <div className="topbar-left">
                    <div className="window-actions">
                        <span className="action-dot close" title="Đóng" />
                        <span className="action-dot minimize" title="Thu nhỏ" />
                        <span className="action-dot zoom" title="Mở rộng" />
                    </div>

                    <button
                        type="button"
                        className="btn-toggle-sidebar"
                        onClick={this.props.dispatchToggleSidebar}
                        title={isSidebarOpen ? 'Ẩn thanh bên' : 'Hiện thanh bên'}
                    >
                        <i className={`fas fa-table-columns ${!isSidebarOpen ? 'opacity-50' : ''}`} />
                    </button>
                </div>

                {/* Center: Segmented Navigation & Omni URL Bar */}
                <div className="topbar-center">
                    <div className="omnibar-search">
                        <i className={`fas fa-lock lock-icon ${isOnline ? 'text-success' : 'text-danger'}`} />
                        <span className="omnibar-host">127.0.0.1:8000</span>
                        <span className="omnibar-path">/api/v1/rag</span>
                    </div>

                    <div className="nav-segmented-tabs">
                        <button
                            type="button"
                            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
                            onClick={() => this.handleTabChange('chat')}
                        >
                            <i className="fas fa-comment-dots" />
                            <span>Hỏi Đáp AI</span>
                        </button>

                        <button
                            type="button"
                            className={`tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
                            onClick={() => this.handleTabChange('documents')}
                        >
                            <i className="fas fa-folder-open" />
                            <span>Kho Tài Liệu</span>
                        </button>

                        <button
                            type="button"
                            className={`tab-btn ${activeTab === 'system' ? 'active' : ''}`}
                            onClick={() => this.handleTabChange('system')}
                        >
                            <i className="fas fa-server" />
                            <span>Hệ Thống RAG</span>
                        </button>
                    </div>
                </div>

                {/* Right side: Health & Quick Actions */}
                <div className="topbar-right">
                    <div className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
                        <span className="status-dot" />
                        <span>{isOnline ? 'FastAPI Sẵn sàng' : 'Ngoại tuyến'}</span>
                    </div>

                    {activeTab === 'chat' && (
                        <button
                            type="button"
                            className="btn btn-sm btn-primary rounded-pill px-3 ms-2"
                            onClick={this.handleNewChat}
                            title="Tạo cuộc hội thoại mới"
                        >
                            <i className="fas fa-plus me-1" />
                            <span>Chat Mới</span>
                        </button>
                    )}
                </div>
            </header>
        );
    }
}

const mapStateToProps = (state) => ({
    activeTab: state.app.activeTab,
    isSidebarOpen: state.app.isSidebarOpen,
    backendHealth: state.app.backendHealth
});

const mapDispatchToProps = (dispatch) => ({
    dispatchSetActiveTab: (tab) => dispatch(setActiveTab(tab)),
    dispatchToggleSidebar: () => dispatch(toggleSidebar()),
    dispatchCheckHealth: () => dispatch(checkBackendHealth()),
    dispatchCreateNewSession: (title) => dispatch(createNewSession(title))
});

export default connect(mapStateToProps, mapDispatchToProps)(HeaderToolbar);
