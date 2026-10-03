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
    timeout: 60000
});

// Response interceptor to extract data and format friendly errors
instance.interceptors.response.use(
    (response) => response.data,
    (error) => {
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
