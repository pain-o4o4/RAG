import React, { Component } from 'react';
import { connect } from 'react-redux';
import { loginUserThunk, registerUserThunk } from '../../store/actions/userActions';
import { fetchChatSessions } from '../../store/actions/ragActions';
import { ToastUtil } from '../../utils/ToastUtil';

class AuthModal extends Component {
    state = {
        activeTab: 'login', // 'login' | 'register'
        email: '',
        password: '',
        userName: '',
        isLoading: false
    };

    handleTabSwitch = (tab) => {
        this.setState({ activeTab: tab });
    };

    handleInputChange = (field, value) => {
        this.setState({ [field]: value });
    };

    handleSubmit = async (e) => {
        e.preventDefault();
        const { activeTab, email, password, userName, isLoading } = this.state;

        if (isLoading) return;

        if (!email.trim() || !password.trim()) {
            ToastUtil.warn('Vui lòng nhập đầy đủ Email và Mật khẩu.');
            return;
        }

        if (activeTab === 'register' && !userName.trim()) {
            ToastUtil.warn('Vui lòng nhập Tên hiển thị.');
            return;
        }

        this.setState({ isLoading: true });

        if (activeTab === 'login') {
            await this.props.dispatchLogin(email.trim(), password.trim(), () => {
                this.setState({
                    email: '',
                    password: '',
                    userName: '',
                    isLoading: false
                });
                this.props.dispatchFetchSessions();
                if (this.props.onClose) {
                    this.props.onClose();
                }
            });
            this.setState({ isLoading: false });
        } else {
            await this.props.dispatchRegister(userName.trim(), email.trim(), password.trim(), () => {
                this.setState({
                    activeTab: 'login',
                    password: '',
                    isLoading: false
                });
            });
            this.setState({ isLoading: false });
        }
    };

    render() {
        const { isOpen, onClose } = this.props;
        const { activeTab, email, password, userName, isLoading } = this.state;

        if (!isOpen) return null;

        return (
            <div className="auth-modal-overlay" onClick={onClose}>
                <div className="auth-modal-content" onClick={(e) => e.stopPropagation()}>
                    <div className="auth-modal-header">
                        <div className="auth-tabs">
                            <button
                                type="button"
                                className={`auth-tab-btn ${activeTab === 'login' ? 'active' : ''}`}
                                onClick={() => this.handleTabSwitch('login')}
                                disabled={isLoading}
                            >
                                Đăng Nhập
                            </button>
                            <button
                                type="button"
                                className={`auth-tab-btn ${activeTab === 'register' ? 'active' : ''}`}
                                onClick={() => this.handleTabSwitch('register')}
                                disabled={isLoading}
                            >
                                Đăng Ký
                            </button>
                        </div>

                        <button type="button" className="btn-close-auth" onClick={onClose} disabled={isLoading}>
                            <i className="fas fa-times" />
                        </button>
                    </div>

                    <form onSubmit={this.handleSubmit} className="auth-form-body">
                        {activeTab === 'register' && (
                            <div className="form-group mb-3">
                                <label className="form-label">Tên hiển thị</label>
                                <input
                                    type="text"
                                    className="form-control auth-input"
                                    placeholder="Ví dụ: Nguyễn Văn A"
                                    value={userName}
                                    onChange={(e) => this.handleInputChange('userName', e.target.value)}
                                    required={activeTab === 'register'}
                                    disabled={isLoading}
                                />
                            </div>
                        )}

                        <div className="form-group mb-3">
                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                className="form-control auth-input"
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => this.handleInputChange('email', e.target.value)}
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <div className="form-group mb-4">
                            <label className="form-label">Mật khẩu</label>
                            <input
                                type="password"
                                className="form-control auth-input"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => this.handleInputChange('password', e.target.value)}
                                required
                                disabled={isLoading}
                            />
                        </div>

                        <button type="submit" className="btn btn-auth-submit w-100" disabled={isLoading}>
                            {isLoading ? (
                                <span><i className="fas fa-spinner fa-spin me-2" /> Đang xử lý...</span>
                            ) : (
                                activeTab === 'login' ? 'Đăng Nhập' : 'Tạo Tài Khoản'
                            )}
                        </button>
                    </form>
                </div>
            </div>
        );
    }
}

const mapDispatchToProps = (dispatch) => ({
    dispatchLogin: (email, password, onSuccess) => dispatch(loginUserThunk(email, password, onSuccess)),
    dispatchRegister: (userName, email, password, onSuccess) => dispatch(registerUserThunk(userName, email, password, onSuccess)),
    dispatchFetchSessions: () => dispatch(fetchChatSessions())
});

export default connect(null, mapDispatchToProps)(AuthModal);
