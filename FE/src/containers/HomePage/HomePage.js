import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import { Header, Footer } from '../../components';
import { checkBackendHealth } from '../../store/actions';
import { path } from '../../utils/constant';
import withRouter from '../../hoc/withRouter';
import './HomePage.scss';

class HomePage extends Component {
    componentDidMount() {
        this.props.checkHealth();
    }

    render() {
        const { backendHealth } = this.props;
        const isHealthy = backendHealth?.status === 'healthy';

        return (
            <div className="homepage-wrapper">
                <Header />

                <main className="hero-section text-center">
                    <div className="hero-container">
                        {/* Live Backend Health Badge */}
                        <div className="mb-3">
                            <span
                                className={`badge-pill ${isHealthy ? 'bg-success bg-opacity-10 text-success border border-success border-opacity-25' : 'bg-warning bg-opacity-10 text-warning border border-warning border-opacity-25'}`}
                            >
                                <span
                                    className={`spinner-grow spinner-grow-sm me-2 ${isHealthy ? 'text-success' : 'text-warning'}`}
                                    role="status"
                                />
                                Python Backend API:{' '}
                                <strong>
                                    {backendHealth?.status
                                        ? backendHealth.status.toUpperCase()
                                        : 'Checking status...'}
                                </strong>
                            </span>
                        </div>

                        <h1 className="hero-title">
                            Hệ Thống Trợ Lý AI RAG (Retrieval-Augmented Generation)
                        </h1>
                        <p className="hero-subtitle">
                            Tra cứu tài liệu thông minh với Google Gemini 2.5 Flash, PostgreSQL Vector Store và FastAPI Backend.
                        </p>

                        <div className="hero-cta mt-4 d-flex justify-content-center gap-3">
                            <Link to={path.CHAT} className="btn btn-primary btn-lg px-4 cta-btn">
                                <i className="fas fa-comments me-2" />
                                Bắt Đầu Hỏi Đáp
                            </Link>
                            <Link to={path.DOCUMENTS} className="btn btn-outline-primary btn-lg px-4 cta-btn">
                                <i className="fas fa-folder-open me-2" />
                                Quản Lý Tài Liệu
                            </Link>
                        </div>
                    </div>
                </main>

                <section className="features-section py-5">
                    <div className="container">
                        <div className="text-center mb-5">
                            <h2 className="section-title">Kiến Trúc Tích Hợp Python Backend</h2>
                            <p className="section-subtitle text-muted">
                                Kết nối trực tiếp giữa giao diện ReactJS với API dịch vụ FastAPI & Vector Database
                            </p>
                        </div>

                        <div className="row g-4">
                            <div className="col-md-4">
                                <div className="feature-card">
                                    <div className="icon-wrapper mb-3">
                                        <i className="fas fa-robot text-primary fs-3" />
                                    </div>
                                    <h3 className="card-title">LLM Gemini 2.5 Flash</h3>
                                    <p className="card-text">
                                        Sinh câu trả lời chính xác dựa trên ngữ cảnh trích xuất từ tài liệu, kèm nguồn trích dẫn.
                                    </p>
                                </div>
                            </div>

                            <div className="col-md-4">
                                <div className="feature-card">
                                    <div className="icon-wrapper mb-3">
                                        <i className="fas fa-layer-group text-success fs-3" />
                                    </div>
                                    <h3 className="card-title">Text Embedding & Chunks</h3>
                                    <p className="card-text">
                                        Mô hình text-embedding-004 cắt nhỏ tài liệu (chunk size 500) và tính toán vector tương đồng.
                                    </p>
                                </div>
                            </div>

                            <div className="col-md-4">
                                <div className="feature-card">
                                    <div className="icon-wrapper mb-3">
                                        <i className="fas fa-database text-warning fs-3" />
                                    </div>
                                    <h3 className="card-title">PostgreSQL & Async SQLAlchemy</h3>
                                    <p className="card-text">
                                        Quản lý phiên trò chuyện, tin nhắn và danh mục tài liệu bất đồng bộ hiệu năng cao.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <Footer />
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    isLoggedIn: state.user.isLoggedIn,
    userInfo: state.user.userInfo,
    backendHealth: state.app.backendHealth
});

const mapDispatchToProps = (dispatch) => ({
    checkHealth: () => dispatch(checkBackendHealth())
});

export default connect(mapStateToProps, mapDispatchToProps)(withRouter(HomePage));
