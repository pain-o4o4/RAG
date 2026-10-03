import actionTypes from './actionTypes';

export const socketConnect = () => ({
    type: actionTypes.SOCKET_CONNECT
});

export const socketDisconnect = () => ({
    type: actionTypes.SOCKET_DISCONNECT
});
