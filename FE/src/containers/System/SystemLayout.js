import React, { Component } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { connect } from 'react-redux';
import { processLogout } from '../../store/actions';
import { handleLogout } from '../../auth/axiosInstance';
import { path } from '../../utils/constant';
import withRouter from '../../hoc/withRouter';
import './SystemLayout.scss';

class SystemLayout extends Component {
    onLogout = () => {
        handleLogout();
        this.props.dispatchLogout();
        this.props.navigate(path.HOME);
    };

    render() {
        const { userInfo, navigate } = this.props;

        return (
            <div className="system-layout">
                <aside className="system-sidebar">
                    <div className="sidebar-brand">
                        <h3>RAG Admin</h3>
                    </div>

                    <nav className="sidebar-nav">
                        <NavLink
                            to={path.DASHBOARD}
                            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                        >
                            <i className="fas fa-tachometer-alt icon" />
                            <span>Bảng Điều Khiển</span>
                        </NavLink>
                        <NavLink
                            to={path.DOCUMENTS}
                            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                        >
                            <i className="fas fa-folder-open icon" />
                            <span>Kho Tài Liệu</span>
                        </NavLink>
                        <NavLink
                            to={path.CHAT}
                            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                        >
                            <i className="fas fa-comments icon" />
                            <span>Hỏi Đáp AI</span>
                        </NavLink>
                    </nav>

                    <div className="sidebar-footer">
                        <button className="btn-home" onClick={() => navigate(path.HOME)}>
                            <i className="fas fa-home me-2" />
                            <span>Trang Chủ</span>
                        </button>
                        <button className="btn-logout" onClick={this.onLogout}>
                            <i className="fas fa-sign-out-alt me-2" />
                            <span>Đăng Xuất</span>
                        </button>
                    </div>
                </aside>

                <div className="system-main">
                    <header className="system-topbar">
                        <div className="topbar-title">
                            <h4>Hệ Thống Trợ Lý RAG</h4>
                        </div>
                        <div className="topbar-user">
                            <span>
                                Xin chào, <strong>{userInfo?.user_name || userInfo?.email || 'Admin'}</strong>
                            </span>
                        </div>
                    </header>

                    <main className="system-content">
                        <Outlet />
                    </main>
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    userInfo: state.user.userInfo
});

const mapDispatchToProps = (dispatch) => ({
    dispatchLogout: () => dispatch(processLogout())
});

export default connect(mapStateToProps, mapDispatchToProps)(withRouter(SystemLayout));
