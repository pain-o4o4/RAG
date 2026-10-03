import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import { registerUserThunk } from '../../store/actions';
import { path } from '../../utils/constant';
import withRouter from '../../hoc/withRouter';
import './Login.scss';

class Register extends Component {
    state = {
        user_name: '',
        email: '',
        password: '',
        confirmPassword: '',
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

    handleRegister = async (e) => {
        e.preventDefault();
        const { user_name, email, password, confirmPassword } = this.state;
        const { dispatchRegister, navigate } = this.props;

        this.setState({ errorMessage: '' });

        if (!user_name.trim() || !email.trim() || !password.trim()) {
            this.setState({ errorMessage: 'Vui lòng điền đầy đủ các trường thông tin.' });
            return;
        }

        if (user_name.trim().length < 3) {
            this.setState({ errorMessage: 'Tên đăng nhập phải có ít nhất 3 ký tự.' });
            return;
        }

        if (password.length < 6) {
            this.setState({ errorMessage: 'Mật khẩu phải có ít nhất 6 ký tự.' });
            return;
        }

        if (password !== confirmPassword) {
            this.setState({ errorMessage: 'Mật khẩu xác nhận không khớp!' });
            return;
        }

        this.setState({ isLoading: true });
        dispatchRegister(user_name.trim(), email.trim(), password, () => {
            this.setState({ isLoading: false });
            navigate(path.LOGIN);
        });
        this.setState({ isLoading: false });
    };

    render() {
        const { user_name, email, password, confirmPassword, isShowPassword, isLoading, errorMessage } = this.state;

        return (
            <div className="login-wrapper">
                <div className="login-card">
                    <div className="login-header text-center">
                        <div className="mb-2">
                            <span className="badge bg-success bg-opacity-10 text-success px-3 py-2 rounded-pill">
                                <i className="fas fa-user-plus me-1" /> Tạo Tài Khoản
                            </span>
                        </div>
                        <h2 className="title">Đăng Ký Tài Khoản</h2>
                        <p className="subtitle">Tham gia hệ thống hỏi đáp RAG AI</p>
                    </div>

                    {errorMessage && (
                        <div className="alert alert-danger py-2 px-3 mb-3" role="alert">
                            {errorMessage}
                        </div>
                    )}

                    <form onSubmit={this.handleRegister} className="login-form">
                        <div className="form-group mb-3">
                            <label className="form-label">Tên người dùng (Username)</label>
                            <div className="input-group">
                                <span className="input-group-text">
                                    <i className="fas fa-user" />
                                </span>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="john_doe"
                                    value={user_name}
                                    onChange={(e) => this.handleInputChange('user_name', e.target.value)}
                                    disabled={isLoading}
                                    autoFocus
                                    required
                                />
                            </div>
                        </div>

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
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group mb-3">
                            <label className="form-label">Mật khẩu</label>
                            <div className="input-group">
                                <span className="input-group-text">
                                    <i className="fas fa-lock" />
                                </span>
                                <input
                                    type={isShowPassword ? 'text' : 'password'}
                                    className="form-control"
                                    placeholder="Ít nhất 6 ký tự"
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

                        <div className="form-group mb-4">
                            <label className="form-label">Xác nhận mật khẩu</label>
                            <div className="input-group">
                                <span className="input-group-text">
                                    <i className="fas fa-check-double" />
                                </span>
                                <input
                                    type={isShowPassword ? 'text' : 'password'}
                                    className="form-control"
                                    placeholder="Nhập lại mật khẩu"
                                    value={confirmPassword}
                                    onChange={(e) => this.handleInputChange('confirmPassword', e.target.value)}
                                    disabled={isLoading}
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-success w-100 py-2 btn-submit"
                            disabled={isLoading}
                        >
                            {isLoading && (
                                <span className="spinner-border spinner-border-sm me-2" role="status" />
                            )}
                            Đăng Ký
                        </button>
                    </form>

                    <div className="text-center mt-3 small text-muted">
                        Đã có tài khoản?{' '}
                        <Link to={path.LOGIN} className="fw-bold text-primary">
                            Đăng nhập
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
    dispatchRegister: (user_name, email, password, onSuccess) =>
        dispatch(registerUserThunk(user_name, email, password, onSuccess))
});

export default connect(null, mapDispatchToProps)(withRouter(Register));
