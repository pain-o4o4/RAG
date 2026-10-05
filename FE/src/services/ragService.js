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

/**
 * Gửi câu hỏi và nhận phản hồi dạng stream (SSE) qua fetch + ReadableStream.
 * axios không hỗ trợ đọc stream trên trình duyệt nên dùng fetch.
 * callbacks: { onSources(list), onToken(text), onDone() }
 */
export const streamChatMessageApi = async (sessionId, content, userId, callbacks = {}) => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    const res = await fetch(`${backendUrl}/api/v1/chat/sessions/${sessionId}/messages/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(userId ? { 'X-User-Id': userId } : {})
        },
        body: JSON.stringify({ content })
    });

    if (!res.ok || !res.body) {
        let msg = 'Lỗi khi nhận câu trả lời từ RAG AI.';
        try {
            const err = await res.json();
            if (typeof err?.detail === 'string') msg = err.detail;
        } catch (_) { /* ignore */ }
        const error = new Error(msg);
        error.friendlyMessage = msg;
        throw error;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    const handleEvent = (rawEvent) => {
        let eventName = 'message';
        const dataLines = [];
        rawEvent.split('\n').forEach((line) => {
            if (line.startsWith('event:')) eventName = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        });
        const data = dataLines.join('\n');
        if (eventName === 'done' || data === '[DONE]') {
            callbacks.onDone && callbacks.onDone();
            return;
        }
        try {
            const parsed = JSON.parse(data);
            if (eventName === 'sources') callbacks.onSources && callbacks.onSources(parsed);
            else if (eventName === 'token') callbacks.onToken && callbacks.onToken(parsed.text || '');
        } catch (_) { /* bỏ qua event lỗi định dạng */ }
    };

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r/g, '');
        // Mỗi SSE event kết thúc bằng một dòng trống
        let sepIndex;
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, sepIndex);
            buffer = buffer.slice(sepIndex + 2);
            if (rawEvent.trim()) handleEvent(rawEvent);
        }
    }
    if (buffer.trim()) handleEvent(buffer);
};

export const uploadAndChatNewSessionApi = (formData) => {
    return axios.post('/api/v1/chat/sessions/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};

export const uploadAndChatExistingSessionApi = (sessionId, formData) => {
    return axios.post(`/api/v1/chat/sessions/${sessionId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};

