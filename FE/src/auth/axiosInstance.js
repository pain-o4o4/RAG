import axios from 'axios';

const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

let store = null;

export const injectStore = (_store) => {
    store = _store;
};

export const handleLogout = () => {
    if (store && store.dispatch) {
        // Optional logout dispatch
    }
};

const instance = axios.create({
    baseURL: backendUrl,
    timeout: 300000
});

// Request interceptor: attach X-User-Id header for authenticated requests
instance.interceptors.request.use(
    (config) => {
        if (store) {
            const state = store.getState();
            const userInfo = state?.user?.userInfo;
            if (userInfo && userInfo.id && typeof userInfo.id === 'string' && userInfo.id.length > 10) {
                config.headers['X-User-Id'] = userInfo.id;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor to extract data and format friendly errors
instance.interceptors.response.use(
    (response) => response.data,
    (error) => {
        if (error.response?.status === 401 && store) {
            // Clear invalid session from storage
            store.dispatch({ type: 'PROCESS_LOGOUT' });
        }

        let errorMsg = 'Lỗi kết nối máy chủ Python.';
        const detail = error.response?.data?.detail;

        if (typeof detail === 'string') {
            errorMsg = detail;
        } else if (Array.isArray(detail)) {
            errorMsg = detail.map((d) => d.msg || d.message || JSON.stringify(d)).join(', ');
        } else if (error.message) {
            errorMsg = error.message;
        }

        error.friendlyMessage = errorMsg;
        return Promise.reject(error);
    }
);

export default instance;
