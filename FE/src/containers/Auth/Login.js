import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import { handleLoginApi } from '../../services/userService';
import { userLoginSuccess } from '../../store/actions';
import { ToastUtil } from '../../utils/ToastUtil';
import { path } from '../../utils/constant';
import withRouter from '../../hoc/withRouter';
import './Login.scss';

class Login extends Component {
    state = {
        email: '',
        password: '',
        isShowPassword: false,
        isLoading: false,
        errorMessage: ''
    };

    handleInputChange = (field, value) => {
        this.setState({ [field]: value });
    };

    handleTogglePassword = () => {
        this.setState((prevState) => ({
            isShowPassword: !prevState.isShowPassword
        }));
    };

    handleLogin = async (e) => {
        e.preventDefault();
        const { email, password } = this.state;
        const { dispatchLoginSuccess, navigate } = this.props;

        this.setState({ errorMessage: '' });

        if (!email.trim() || !password.trim()) {
            this.setState({ errorMessage: 'Vui lòng nhập đầy đủ Email và Mật khẩu.' });
            return;
        }

        this.setState({ isLoading: true });
        try {
            const data = await handleLoginApi(email, password);

            if (data && data.user) {
                dispatchLoginSuccess(data.user);
                ToastUtil.success(data.message || 'Đăng nhập thành công!');
                navigate(path.HOME);
            } else {
                const msg = data?.message || 'Email hoặc mật khẩu không chính xác.';
                this.setState({ errorMessage: msg });
                ToastUtil.error(msg);
            }
        } catch (error) {
            console.error('Login error:', error);
            const msg = error.friendlyMessage || 'Lỗi kết nối máy chủ Python Backend.';
            this.setState({ errorMessage: msg });
            ToastUtil.error(msg);
        } finally {
            this.setState({ isLoading: false });
        }
    };

    render() {
        const { email, password, isShowPassword, isLoading, errorMessage } = this.state;

        return (
            <div className="login-wrapper">
                <div className="login-card">
                    <div className="login-header text-center">
                        <div className="mb-2">
                            <span className="badge bg-primary bg-opacity-10 text-primary px-3 py-2 rounded-pill">
                                <i className="fas fa-brain me-1" /> RAG AI Portal
                            </span>
                        </div>
                        <h2 className="title">Đăng Nhập</h2>
                        <p className="subtitle">Kết nối với Python FastAPI Backend</p>
                    </div>

                    {errorMessage && (
                        <div className="alert alert-danger py-2 px-3 mb-3" role="alert">
                            {errorMessage}
                        </div>
                    )}

                    <form onSubmit={this.handleLogin} className="login-form">
                        <div className="form-group mb-3">
                            <label className="form-label">Địa chỉ Email</label>
                            <div className="input-group">
                                <span className="input-group-text">
                                    <i className="fas fa-envelope" />
                                </span>
                                <input
                                    type="email"
                                    className="form-control"
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => this.handleInputChange('email', e.target.value)}
                                    disabled={isLoading}
                                    autoFocus
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group mb-4">
                            <label className="form-label">Mật khẩu</label>
                            <div className="input-group">
                                <span className="input-group-text">
                                    <i className="fas fa-lock" />
                                </span>
                                <input
                                    type={isShowPassword ? 'text' : 'password'}
                                    className="form-control"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => this.handleInputChange('password', e.target.value)}
                                    disabled={isLoading}
                                    required
                                />
                                <button
                                    type="button"
                                    className="btn btn-outline-secondary"
                                    onClick={this.handleTogglePassword}
                                    tabIndex={-1}
                                >
                                    {isShowPassword ? (
                                        <i className="fas fa-eye-slash" />
                                    ) : (
                                        <i className="fas fa-eye" />
                                    )}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary w-100 py-2 btn-submit"
                            disabled={isLoading}
                        >
                            {isLoading && (
                                <span className="spinner-border spinner-border-sm me-2" role="status" />
                            )}
                            Đăng Nhập
                        </button>
                    </form>

                    <div className="text-center mt-3 small text-muted">
                        Chưa có tài khoản?{' '}
                        <Link to={path.REGISTER} className="fw-bold text-primary">
                            Đăng ký ngay
                        </Link>
                    </div>

                    <div className="login-footer text-center mt-4">
                        <Link to={path.HOME} className="back-link">
                            &larr; Quay lại Trang Chủ
                        </Link>
                    </div>
                </div>
            </div>
        );
    }
}

const mapDispatchToProps = (dispatch) => ({
    dispatchLoginSuccess: (userInfo) => dispatch(userLoginSuccess(userInfo))
});

export default connect(null, mapDispatchToProps)(withRouter(Login));
