import React, { Component } from 'react';
import { connect } from 'react-redux';
import { ToastContainer } from 'react-toastify';
import ConfirmModal from '../components/ConfirmModal';
import ChatSidebar from '../components/Sidebar/ChatSidebar';
import CitationInspector from '../components/Inspector/CitationInspector';
import ChatWorkspace from './Chat/ChatWorkspace';
import DocumentManager from '../components/Documents/DocumentManager';
import { checkBackendHealth } from '../store/actions';
import { fetchChatSessions } from '../store/actions/ragActions';
import './App.scss';

class App extends Component {
    state = {
        bootstrapped: false
    };

    componentDidMount() {
        const { persistor } = this.props;
        if (!persistor) {
            this.setState({ bootstrapped: true });
        } else {
            const { bootstrapped } = persistor.getState();
            if (bootstrapped) {
                this.setState({ bootstrapped: true });
            } else {
                const unsubscribe = persistor.subscribe(() => {
                    const current = persistor.getState();
                    if (current.bootstrapped) {
                        unsubscribe();
                        this.setState({ bootstrapped: true });
                    }
                });
            }
        }

        this.props.dispatchCheckHealth();
        this.props.dispatchFetchSessions();
    }

    render() {
        if (!this.state.bootstrapped) {
            return null;
        }

        const { activeTab, isLoggedIn } = this.props;

        return (
            <div className="rag-app-container">
                <ConfirmModal />

                {/* Left Sidebar: Sessions history & Auth */}
                <ChatSidebar />

                {/* Main Workspace: Chat & Direct Document Upload */}
                <main className="rag-main-content">
                    {activeTab === 'documents' ? (
                        <div className="document-manager-workspace">
                            <DocumentManager isLoggedIn={isLoggedIn} />
                        </div>
                    ) : (
                        <>
                            <ChatWorkspace />
                            <CitationInspector />
                        </>
                    )}
                </main>

                <ToastContainer
                    position="bottom-right"
                    autoClose={3000}
                    hideProgressBar={false}
                    newestOnTop={false}
                    closeOnClick
                    rtl={false}
                    pauseOnFocusLoss
                    draggable
                    pauseOnHover
                    theme="dark"
                />
            </div>
        );
    }
}

const mapStateToProps = (state) => ({
    activeTab: state.app.activeTab,
    isLoggedIn: state.user.isLoggedIn
});

const mapDispatchToProps = (dispatch) => ({
    dispatchCheckHealth: () => dispatch(checkBackendHealth()),
    dispatchFetchSessions: () => dispatch(fetchChatSessions())
});

export default connect(mapStateToProps, mapDispatchToProps)(App);
