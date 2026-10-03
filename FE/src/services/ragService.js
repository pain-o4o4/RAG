import axios from '../auth/axiosInstance';

// ==========================================
// 1. KHO TÀI LIỆU (DOCUMENT MANAGEMENT)
// ==========================================

export const uploadDocumentsApi = (formData) => {
    return axios.post('/api/v1/documents/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    });
};

export const getDocumentsApi = ({ page = 1, limit = 50, status = null, search = null } = {}) => {
    const params = new URLSearchParams();
    if (page) params.append('page', page);
    if (limit) params.append('limit', limit);
    if (status) params.append('status', status);
    if (search && search.trim()) params.append('search', search.trim());

    return axios.get(`/api/v1/documents?${params.toString()}`);
};

export const getDocumentByIdApi = (docId) => {
    return axios.get(`/api/v1/documents/${docId}`);
};

export const deleteDocumentApi = (docId) => {
    return axios.delete(`/api/v1/documents/${docId}`);
};

// ==========================================
// 2. HỎI ĐÁP RAG & PHIÊN CHAT (CHAT & SESSIONS)
// ==========================================

export const getChatSessionsApi = () => {
    return axios.get('/api/v1/chat/sessions');
};

export const createChatSessionApi = (title = 'Cuộc hội thoại mới', document_id = null) => {
    return axios.post('/api/v1/chat/sessions', {
        title,
        document_id
    });
};

export const getChatSessionByIdApi = (sessionId) => {
    return axios.get(`/api/v1/chat/sessions/${sessionId}`);
};

export const updateSessionTitleApi = (sessionId, title) => {
    return axios.patch(`/api/v1/chat/sessions/${sessionId}`, { title });
};

export const deleteChatSessionApi = (sessionId) => {
    return axios.delete(`/api/v1/chat/sessions/${sessionId}`);
};

export const getChatMessagesApi = (sessionId) => {
    return axios.get(`/api/v1/chat/sessions/${sessionId}/messages`);
};

export const sendChatMessageApi = (sessionId, content) => {
    return axios.post(`/api/v1/chat/sessions/${sessionId}/messages`, { content });
};

// ==========================================
// 3. SYSTEM HEALTH CHECK & AUTH STUBS
// ==========================================

export const getHealthCheckApi = () => {
    return axios.get('/health');
};

export const handleLoginApi = (email, password) => {
    return Promise.resolve({
        user: { id: 1, email: email || 'admin@rag.local', user_name: 'Admin' },
        message: 'Đăng nhập thành công'
    });
};

export const handleRegisterApi = (user_name, email, password) => {
    return Promise.resolve({
        id: 1,
        user_name,
        email,
        message: 'Đăng ký thành công'
    });
};

export const handleLogoutApi = () => {
    return Promise.resolve({ message: 'Đã đăng xuất' });
};
