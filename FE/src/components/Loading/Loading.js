import React, { Component } from 'react';
import './Loading.scss';

class Loading extends Component {
    render() {
        const { text = 'Đang tải dữ liệu...' } = this.props;
        return (
            <div className="app-loading-container">
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading...</span>
                </div>
                {text && <p className="loading-text">{text}</p>}
            </div>
        );
    }
}

export default Loading;
