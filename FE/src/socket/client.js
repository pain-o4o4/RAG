import { io } from 'socket.io-client';

let socket = null;

export const initSocket = (token) => {
    if (socket && socket.connected) {
        return socket;
    }

    const socketUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8080';

    socket = io(socketUrl, {
        auth: {
            token: token || localStorage.getItem('token')
        },
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 2000
    });

    socket.on('connect', () => {
        console.log('[Socket] Connected to server, ID:', socket.id);
    });

    socket.on('disconnect', (reason) => {
        console.log('[Socket] Disconnected:', reason);
    });

    socket.on('connect_error', (error) => {
        console.warn('[Socket] Connection error:', error.message);
    });

    return socket;
};

export const getSocket = () => socket;

export const disconnectSocket = () => {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
};
