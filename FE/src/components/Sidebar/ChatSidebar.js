import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
    fetchChatSessions,
    setActiveSession,
    createNewSession,
    deleteSession
} from '../../store/actions/ragActions';
import { processLogout } from '../../store/actions/userActions';
import { toggleSidebar } from '../../store/actions';
import AuthModal from '../Auth/AuthModal';

class ChatSidebar extends Component {
    state = {
        searchQuery: '',
        isAuthModalOpen: false,
        showUserMenu: false
    };

    searchInputRef = React.createRef();

    componentDidMount() {
        if (this.props.isLoggedIn) {
            this.props.dispatchFetchSessions();
        }
    }

    componentDidUpdate(prevProps) {
        if (!prevProps.isLoggedIn && this.props.isLoggedIn) {
            this.props.dispatchFetchSessions();
        }
    }

    handleSearchChange = (e) => {
        this.setState({ searchQuery: e.target.value });
    };

    handleNewChat = () => {
        this.props.dispatchSetActiveSession(null);
    };

    handleSelectSession = (sessionId) => {
        this.props.dispatchSetActiveSession(sessionId);
    };

    handleDeleteSession = (e, sessionId) => {
        e.stopPropagation();
        if (window.confirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')) {
            this.props.dispatchDeleteSession(sessionId);
        }
    };

    handleOpenAuthModal = () => {
        this.setState({ isAuthModalOpen: true, showUserMenu: false });
    };

    handleCloseAuthModal = () => {
        this.setState({ isAuthModalOpen: false });
    };

    handleToggleUserMenu = () => {
        this.setState((prev) => ({ showUserMenu: !prev.showUserMenu }));
    };

    handleLogout = (e) => {
        if (e) e.stopPropagation();
        this.props.dispatchLogout();
        this.setState({ showUserMenu: false });
    };

    handleExpandAndSearch = () => {
        if (!this.props.isSidebarOpen) {
            this.props.dispatchToggleSidebar();
        }
        setTimeout(() => {
            if (this.searchInputRef.current) {
                this.searchInputRef.current.focus();
            }
        }, 150);
    };

    getUserInitials = (name) => {
        if (!name) return 'U';
        const parts = name.trim().split(' ');
        if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    };

    render() {
        const { sessions, activeSessionId, isSidebarOpen, isLoggedIn, userInfo } = this.props;
        const { searchQuery, isAuthModalOpen } = this.state;

        const filteredSessions = (sessions || []).filter((s) =>
            s.title?.toLowerCase().includes(searchQuery.toLowerCase())
        );

        return (
            <>
                <aside className={`grok-side-nav ${!isSidebarOpen ? 'collapsed' : ''}`}>
                    {/* Collapsed Strip View */}
                    {!isSidebarOpen ? (
                        <div className="collapsed-icon-strip">
                            {/* Top Controls */}
                            <div className="strip-top-group">
                                <button
                                    type="button"
                                    className="strip-btn toggle-btn"
                                    onClick={this.props.dispatchToggleSidebar}
                                    title="Mở rộng thanh bên"
                                >
                                    <i className="fas fa-table-columns" />
                                </button>

                                <button
                                    type="button"
                                    className="strip-btn"
                                    onClick={this.handleExpandAndSearch}
                                    title="Tìm kiếm hội thoại"
                                >
                                    <i className="fas fa-search" />
                                </button>

                                <button
                                    type="button"
                                    className="strip-btn new-chat-pill-btn"
                                    onClick={this.handleNewChat}
                                    title="Cuộc trò chuyện mới"
                                >
                                    <i className="far fa-edit" />
                                </button>

                                <div className="strip-divider" />

                                <button
                                    type="button"
                                    className="strip-btn"
                                    onClick={this.handleExpandAndSearch}
                                    title="Lịch sử hội thoại"
                                >
                                    <i className="fas fa-clock-rotate-left" />
                                </button>
                            </div>

                            {/* Bottom Controls */}
                            <div className="strip-bottom-group">
                                {isLoggedIn && userInfo ? (
                                    <div
                                        className="strip-avatar-btn"
                                        onClick={this.handleToggleUserMenu}
                                        title={`Tài khoản: ${userInfo.user_name || userInfo.email} (Nhấp để đăng xuất)`}
                                    >
                                        <div className="avatar-circle">
                                            {this.getUserInitials(userInfo.user_name || userInfo.email)}
                                        </div>
                                    </div>
                                ) : (
                                    <button
                                        type="button"
                                        className="strip-btn auth-login-btn"
                                        onClick={this.handleOpenAuthModal}
                                        title="Đăng nhập / Đăng ký"
                                    >
                                        <i className="far fa-circle-user" />
                                    </button>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* Expanded Full Sidebar View */
                        <div className="expanded-sidebar-content">
                            {/* Brand Header */}
                            <div className="sidebar-top-header">
                                <div className="brand-logo" onClick={this.handleNewChat} title="RAG AI Assistant">
                                    <i className="fas fa-brain brand-icon" />
                                    <span className="brand-name">RAG AI</span>
                                </div>

                                <button
                                    type="button"
                                    className="btn-toggle-sidebar"
                                    onClick={this.props.dispatchToggleSidebar}
                                    title="Thu gọn thanh bên"
                                >
                                    <i className="fas fa-table-columns" />
                                </button>
                            </div>

                            {/* New Chat Primary Action */}
                            <div className="sidebar-action-bar">
                                <button
                                    type="button"
                                    className="btn-new-chat-main"
                                    onClick={this.handleNewChat}
                                >
                                    <i className="far fa-edit me-2" />
                                    <span>Cuộc trò chuyện mới</span>
                                </button>
                            </div>

                            {/* Search Box */}
                            {isLoggedIn && (
                                <div className="sidebar-search-wrapper">
                                    <div className="search-input-box">
                                        <i className="fas fa-search search-icon" />
                                        <input
                                            ref={this.searchInputRef}
                                            type="text"
                                            placeholder="Tìm kiếm lịch sử..."
                                            value={searchQuery}
                                            onChange={this.handleSearchChange}
                                        />
                                        {searchQuery && (
                                            <button
                                                type="button"
                                                className="btn-clear-search"
                                                onClick={() => this.setState({ searchQuery: '' })}
                                            >
                                                <i className="fas fa-times" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Sessions History List */}
                            <div className="sidebar-sessions-list">
                                <div className="sessions-header-label">
                                    <span>LỊCH SỬ HỘI THOẠI</span>
                                    {isLoggedIn && filteredSessions.length > 0 && (
                                        <span className="sessions-count">({filteredSessions.length})</span>
                                    )}
                                </div>

                                {isLoggedIn ? (
                                    filteredSessions.length > 0 ? (
                                        filteredSessions.map((session) => {
                                            const isActive = session.id === activeSessionId;
                                            return (
                                                <div
                                                    key={session.id}
                                                    className={`session-card-item ${isActive ? 'active' : ''}`}
                                                    onClick={() => this.handleSelectSession(session.id)}
                                                >
                                                    <i className="far fa-message item-icon" />
                                                    <span className="session-title-text" title={session.title}>
                                                        {session.title || 'Cuộc trò chuyện mới'}
                                                    </span>
                                                    <button
                                                        type="button"
                                                        className="btn-delete-session"
                                                        onClick={(e) => this.handleDeleteSession(e, session.id)}
                                                        title="Xóa cuộc trò chuyện"
                                                    >
                                                        <i className="far fa-trash-can" />
                                                    </button>
                                                </div>
                                            );
                                        })
                                    ) : (
                                        <div className="empty-history-text">
                                            {searchQuery ? 'Không tìm thấy kết quả phù hợp' : 'Chưa có lịch sử hội thoại'}
                                        </div>
                                    )
                                ) : (
                                    <div className="empty-history-text py-4 text-center">
                                        <i className="fas fa-lock text-muted mb-2 d-block fs-5" />
                                        <span>Đăng nhập để xem và lưu trữ lịch sử cuộc trò chuyện</span>
                                    </div>
                                )}
                            </div>

                            {/* User Account / Auth Footer */}
                            <div className="sidebar-bottom-account">
                                {isLoggedIn && userInfo ? (
                                    <div className="user-logged-box">
                                        <div className="user-avatar-pill">
                                            {this.getUserInitials(userInfo.user_name || userInfo.email)}
                                        </div>
                                        <div className="user-details" title={userInfo.email}>
                                            <div className="user-name-text">
                                                {userInfo.user_name || 'Người dùng'}
                                            </div>
                                            <div className="user-email-text">
                                                {userInfo.email || ''}
                                            </div>
                                        </div>
                                        <button
                                            type="button"
                                            className="btn-logout-icon"
                                            onClick={this.handleLogout}
                                            title="Đăng xuất"
                                        >
                                            <i className="fas fa-arrow-right-from-bracket" />
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        type="button"
                                        className="btn-auth-trigger"
                                        onClick={this.handleOpenAuthModal}
                                    >
                                        <i className="far fa-circle-user me-2 fs-5" />
                                        <span>Đăng nhập / Đăng ký</span>
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </aside>

                {/* Authentication Modal */}
                <AuthModal
                    isOpen={isAuthModalOpen}
                    onClose={this.handleCloseAuthModal}
                />
            </>
        );
    }
}

const mapStateToProps = (state) => ({
    sessions: state.rag.sessions,
    activeSessionId: state.rag.activeSessionId,
    isSidebarOpen: state.app.isSidebarOpen,
    isLoggedIn: state.user.isLoggedIn,
    userInfo: state.user.userInfo
});

const mapDispatchToProps = (dispatch) => ({
    dispatchFetchSessions: () => dispatch(fetchChatSessions()),
    dispatchSetActiveSession: (id) => dispatch(setActiveSession(id)),
    dispatchCreateNewSession: (title) => dispatch(createNewSession(title)),
    dispatchDeleteSession: (id) => dispatch(deleteSession(id)),
    dispatchToggleSidebar: () => dispatch(toggleSidebar()),
    dispatchLogout: () => dispatch(processLogout())
});

export default connect(mapStateToProps, mapDispatchToProps)(ChatSidebar);
