import React, { Component, createContext } from 'react';
import { connect } from 'react-redux';
import { initSocket, disconnectSocket, getSocket } from '../socket/client';
import { socketConnect, socketDisconnect } from '../store/actions';

export const SocketContext = createContext(null);

class SocketProvider extends Component {
    state = {
        socketInstance: null
    };

    componentDidMount() {
        this.manageSocketConnection();
    }

    componentDidUpdate(prevProps) {
        if (
            prevProps.isLoggedIn !== this.props.isLoggedIn ||
            prevProps.userInfo?.id !== this.props.userInfo?.id
        ) {
            this.manageSocketConnection();
        }
    }

    componentWillUnmount() {
        disconnectSocket();
    }

    manageSocketConnection = () => {
        const { isLoggedIn, userInfo, dispatchSocketConnect, dispatchSocketDisconnect } = this.props;

        if (isLoggedIn && userInfo) {
            const token = localStorage.getItem('token');
            const socket = initSocket(token);
            this.setState({ socketInstance: socket });

            socket.on('connect', () => {
                dispatchSocketConnect();
            });

            socket.on('disconnect', () => {
                dispatchSocketDisconnect();
            });
        } else {
            disconnectSocket();
            this.setState({ socketInstance: null });
        }
    };

    render() {
        const { socketInstance } = this.state;
        const { children } = this.props;

        return (
            <SocketContext.Provider value={{ socket: socketInstance || getSocket() }}>
                {children}
            </SocketContext.Provider>
        );
    }
}

// HOC for class components to consume socket
export const withSocket = (TargetComponent) => {
    return class extends Component {
        render() {
            return (
                <SocketContext.Consumer>
                    {(socketContext) => (
                        <TargetComponent {...this.props} socket={socketContext?.socket} />
                    )}
                </SocketContext.Consumer>
            );
        }
    };
};

const mapStateToProps = (state) => ({
    isLoggedIn: state.user.isLoggedIn,
    userInfo: state.user.userInfo
});

const mapDispatchToProps = (dispatch) => ({
    dispatchSocketConnect: () => dispatch(socketConnect()),
    dispatchSocketDisconnect: () => dispatch(socketDisconnect())
});

export default connect(mapStateToProps, mapDispatchToProps)(SocketProvider);
