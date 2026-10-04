import React, { Component, createContext } from 'react';

export const SocketContext = createContext(null);

class SocketProvider extends Component {
    render() {
        return (
            <SocketContext.Provider value={{ socket: null }}>
                {this.props.children}
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

export default SocketProvider;
