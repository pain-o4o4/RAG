import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Link, NavLink } from 'react-router-dom';
import { processLogout } from '../../store/actions';
import { handleLogout } from '../../auth/axiosInstance';
import { path } from '../../utils/constant';
import withRouter from '../../hoc/withRouter';
import './Header.scss';

class Header extends Component {
    handleUserLogout = () => {
        handleLogout();
        this.props.dispatchLogout();
        this.props.navigate(path.LOGIN);
    };

    render() {
        const { isLoggedIn, userInfo } = this.props;

        return (
            <header className="app-header">
                <div className="header-container">
                    <div className="header-left">
                        <Link to={path.HOME} className="brand-logo d-flex align-items-center gap-2">
                            <i className="fas fa-brain fs-4 text-primary" />
                            <span className="brand-text">RAG Assistant</span>
                        </Link>
                        <nav className="header-nav">
                            <NavLink
                                to={path.HOME}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                Trang Chủ
                            </NavLink>
                            <NavLink
                                to={path.CHAT}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <i className="fas fa-comments me-1" />
                                Hỏi Đáp AI
                            </NavLink>
                            <NavLink
                                to={path.DOCUMENTS}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <i className="fas fa-folder-open me-1" />
                                Tài Liệu
                            </NavLink>
                            <NavLink
                                to={path.DASHBOARD}
                                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            >
                                <i className="fas fa-server me-1" />
                                Hệ Thống
                            </NavLink>
                        </nav>
                    </div>

                    <div className="header-right">
                        {isLoggedIn ? (
                            <div className="user-profile">
                                <div className="user-info">
                                    <i className="fas fa-user-circle fs-5 text-primary" />
                                    <span className="user-name">
                                        {userInfo?.user_name || userInfo?.email || 'User'}
                                    </span>
                                </div>
                                <button
                                    className="btn-logout"
                                    onClick={this.handleUserLogout}
                                    title="Logout"
                                >
                                    <i className="fas fa-sign-out-alt" />
                                    <span className="ms-1 d-none d-md-inline">Đăng Xuất</span>
                                </button>
                            </div>
                        ) : (
                            <div className="auth-actions d-flex gap-2">
                                <Link to={path.LOGIN} className="btn btn-sm btn-outline-primary">
                                    Đăng Nhập
                                </Link>
                                <Link to={path.REGISTER} className="btn btn-sm btn-primary">
                                    Đăng Ký
                                </Link>
                            </div>
                        )}
                    </div>
                </div>
            </header>
        );
    }
}

const mapStateToProps = (state) => ({
    isLoggedIn: state.user.isLoggedIn,
    userInfo: state.user.userInfo
});

const mapDispatchToProps = (dispatch) => ({
    dispatchLogout: () => dispatch(processLogout())
});

export default connect(mapStateToProps, mapDispatchToProps)(withRouter(Header));
