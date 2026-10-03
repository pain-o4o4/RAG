import React, { Component } from 'react';
import './Footer.scss';

class Footer extends Component {
    render() {
        return (
            <footer className="app-footer">
                <div className="footer-container">
                    <p className="copyright">
                        &copy; {new Date().getFullYear()} React Architecture Template. Clean, Modular & Scalable.
                    </p>
                    <div className="footer-links">
                        <span className="badge bg-light text-dark border">React 18</span>
                        <span className="badge bg-light text-dark border">Redux</span>
                        <span className="badge bg-light text-dark border">Axios JWT</span>
                        <span className="badge bg-light text-dark border">Socket.IO</span>
                    </div>
                </div>
            </footer>
        );
    }
}

export default Footer;
