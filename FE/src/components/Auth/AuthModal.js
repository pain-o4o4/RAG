import React, { Component } from 'react';
import { connect } from 'react-redux';
import { userLoginSuccess } from '../../store/actions/userActions';
import { ToastUtil } from '../../utils/ToastUtil';

class AuthModal extends Component {
    state = {
        activeTab: 'login', // 'login' | 'register'
        email: '',
        password: '',
        userName: ''
    };

    handleTabSwitch = (tab) => {
        this.setState({ activeTab: tab });
    };

    handleInputChange = (field, value) => {
        this.setState({ [field]: value });
    };

    handleSubmit = (e) => {
        e.preventDefault();
        const { activeTab, email, password, userName } = this.state;

        if (!email.trim() || !password.trim()) {
            ToastUtil.warn('Vui lòng nhập đầy đủ Email và Mật khẩu.');
            return;
        }

        if (activeTab === 'register' && !userName.trim()) {
            ToastUtil.warn('Vui lòng nhập Tên hiển thị.');
            return;
        }

        const displayName = userName.trim() || email.split('@')[0] || 'User';

        const userPayload = {
            id: Date.now(),
            email: email.trim(),
            user_name: displayName
        };

        this.props.dispatchLoginSuccess(userPayload);
        ToastUtil.success(activeTab === 'login' ? 'Đăng nhập thành công!' : 'Đăng ký tài khoản thành công!');
        
        this.setState({
            email: '',
            password: '',
            userName: ''
        });

        if (this.props.onClose) {
            this.props.onClose();
        }
    };

    render() {
        const { isOpen, onClose } = this.props;
        const { activeTab, email, password, userName } = this.state;

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
                            >
                                Đăng Nhập
                            </button>
                            <button
                                type="button"
                                className={`auth-tab-btn ${activeTab === 'register' ? 'active' : ''}`}
                                onClick={() => this.handleTabSwitch('register')}
                            >
                                Đăng Ký
                            </button>
                        </div>

                        <button type="button" className="btn-close-auth" onClick={onClose}>
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
                            />
                        </div>

                        <button type="submit" className="btn btn-auth-submit w-100">
                            {activeTab === 'login' ? 'Đăng Nhập' : 'Tạo Tài Khoản'}
                        </button>
                    </form>
                </div>
            </div>
        );
    }
}

const mapDispatchToProps = (dispatch) => ({
    dispatchLoginSuccess: (userInfo) => dispatch(userLoginSuccess(userInfo))
});

export default connect(null, mapDispatchToProps)(AuthModal);
