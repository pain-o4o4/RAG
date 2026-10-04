import actionTypes from './actionTypes';
import {
    getDocumentsApi,
    uploadDocumentsApi,
    deleteDocumentApi,
    getChatSessionsApi,
    createChatSessionApi,
    deleteChatSessionApi,
    getChatMessagesApi,
    sendChatMessageApi,
    uploadAndChatNewSessionApi,
    uploadAndChatExistingSessionApi
} from '../../services/userService';
import { ToastUtil } from '../../utils/ToastUtil';

// ==========================================
// DOCUMENTS ACTIONS
// ==========================================

export const fetchDocuments = (params = {}) => {
    return async (dispatch, getState) => {
        const { isLoggedIn } = getState().user;
        if (!isLoggedIn) return;

        dispatch({ type: actionTypes.FETCH_DOCUMENTS_START });
        try {
            const res = await getDocumentsApi(params);
            dispatch({
                type: actionTypes.FETCH_DOCUMENTS_SUCCESS,
                documents: res?.items || (Array.isArray(res) ? res : []),
                total: res?.total || 0,
                totalPages: res?.total_pages || 1
            });
        } catch (e) {
            dispatch({ type: actionTypes.FETCH_DOCUMENTS_FAILED });
            console.warn('Fetch documents failed:', e.friendlyMessage || e.message);
        }
    };
};

export const uploadDocumentsBatch = (files, onSuccess) => {
    return async (dispatch) => {
        dispatch({ type: actionTypes.UPLOAD_DOCUMENT_START });
        try {
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            const res = await uploadDocumentsApi(formData);
            dispatch({ type: actionTypes.UPLOAD_DOCUMENT_SUCCESS, result: res });

            const successCount = res?.successful_uploads?.length || 0;
            const failCount = res?.failed_uploads?.length || 0;

            if (successCount > 0) {
                ToastUtil.success(`Tải lên thành công ${successCount} tài liệu! Đang cập nhật cơ sở tri thức...`);
            }
            if (failCount > 0) {
                ToastUtil.warn(`${failCount} tệp không hợp lệ hoặc đã tồn tại.`);
            }

            dispatch(fetchDocuments());
            if (onSuccess) onSuccess(res);
            return res;
        } catch (e) {
            dispatch({ type: actionTypes.UPLOAD_DOCUMENT_FAILED });
            ToastUtil.error(e.friendlyMessage || 'Tải lên tài liệu thất bại!');
            return null;
        }
    };
};

export const deleteDocument = (docId) => {
    return async (dispatch) => {
        try {
            await deleteDocumentApi(docId);
            ToastUtil.success('Đã xóa tài liệu khỏi kho kiến thức!');
            dispatch(fetchDocuments());
        } catch (e) {
            ToastUtil.error(e.friendlyMessage || 'Không thể xóa tài liệu!');
        }
    };
};

// ==========================================
// CHAT & RAG ACTIONS
// ==========================================

export const fetchChatSessions = () => {
    return async (dispatch) => {
        dispatch({ type: actionTypes.FETCH_SESSIONS_START });
        try {
            const sessions = await getChatSessionsApi();
            dispatch({
                type: actionTypes.FETCH_SESSIONS_SUCCESS,
                sessions: Array.isArray(sessions) ? sessions : []
            });
        } catch (e) {
            console.warn('Fetch sessions error:', e.friendlyMessage || e.message);
        }
    };
};

export const setActiveSession = (sessionId) => {
    return (dispatch) => {
        dispatch({
            type: actionTypes.SET_ACTIVE_SESSION,
            sessionId
        });
        if (sessionId) {
            dispatch(fetchChatMessages(sessionId));
        } else {
            dispatch({
                type: actionTypes.FETCH_MESSAGES_SUCCESS,
                messages: []
            });
        }
    };
};

export const createNewSession = (title = 'Cuộc trò chuyện mới', docId = null) => {
    return async (dispatch) => {
        try {
            const newSession = await createChatSessionApi(title, docId);
            if (newSession && newSession.id) {
                dispatch({
                    type: actionTypes.SET_ACTIVE_SESSION,
                    sessionId: newSession.id
                });
                dispatch({
                    type: actionTypes.FETCH_MESSAGES_SUCCESS,
                    messages: []
                });
                dispatch(fetchChatSessions());
                return newSession;
            }
        } catch (e) {
            ToastUtil.error(e.friendlyMessage || 'Không thể tạo phiên trò chuyện mới.');
        }
    };
};

export const deleteSession = (sessionId) => {
    return async (dispatch, getState) => {
        try {
            await deleteChatSessionApi(sessionId);
            dispatch({ type: actionTypes.DELETE_SESSION_SUCCESS, sessionId });

            const remainingSessions = getState().rag.sessions.filter((s) => s.id !== sessionId);
            if (remainingSessions.length > 0) {
                dispatch(setActiveSession(remainingSessions[0].id));
            } else {
                dispatch(setActiveSession(null));
            }
            ToastUtil.info('Đã xóa phiên trò chuyện.');
        } catch (e) {
            ToastUtil.error(e.friendlyMessage || 'Không thể xóa phiên trò chuyện.');
        }
    };
};

export const fetchChatMessages = (sessionId) => {
    return async (dispatch) => {
        if (!sessionId) {
            dispatch({
                type: actionTypes.FETCH_MESSAGES_SUCCESS,
                messages: []
            });
            return;
        }

        dispatch({ type: actionTypes.FETCH_MESSAGES_START });
        try {
            const messages = await getChatMessagesApi(sessionId);
            dispatch({
                type: actionTypes.FETCH_MESSAGES_SUCCESS,
                messages: Array.isArray(messages) ? messages : []
            });
        } catch (e) {
            console.warn('Fetch messages error:', e.friendlyMessage || e.message);
        }
    };
};

export const sendMessage = (sessionId, content, files = []) => {
    return async (dispatch, getState) => {
        const text = (content || '').trim();
        if (!text && (!files || files.length === 0)) return;

        let activeId = sessionId;
        const tempId = 'temp-' + Date.now();

        // Optimistic UI user message
        const displayContent = text || (files.length > 0 ? `Đã đính kèm ${files.length} tài liệu.` : '');
        dispatch({
            type: actionTypes.ADD_USER_MESSAGE,
            message: {
                id: tempId,
                session_id: activeId,
                role: 'user',
                content: displayContent,
                created_at: new Date().toISOString()
            }
        });

        dispatch({ type: actionTypes.SET_IS_SENDING_MESSAGE, isSending: true });

        try {
            if (files && files.length > 0) {
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                if (text) {
                    formData.append('content', text);
                }

                let res = null;
                if (!activeId) {
                    const previewTitle = text.length > 25 ? text.substring(0, 25) + '...' : files[0].name;
                    formData.append('title', previewTitle);
                    res = await uploadAndChatNewSessionApi(formData);
                    if (res && res.session) {
                        activeId = res.session.id;
                        dispatch({ type: actionTypes.SET_ACTIVE_SESSION, sessionId: activeId });
                        dispatch(fetchChatSessions());
                    }
                } else {
                    res = await uploadAndChatExistingSessionApi(activeId, formData);
                }

                if (res && res.assistant_message) {
                    dispatch({
                        type: actionTypes.ADD_ASSISTANT_MESSAGE,
                        userMessage: res.user_message,
                        assistantMessage: res.assistant_message
                    });
                }
            } else {
                if (!activeId) {
                    const previewTitle = text.length > 25 ? text.substring(0, 25) + '...' : text;
                    const newSession = await createChatSessionApi(previewTitle);
                    if (newSession && newSession.id) {
                        activeId = newSession.id;
                        dispatch({ type: actionTypes.SET_ACTIVE_SESSION, sessionId: activeId });
                        dispatch(fetchChatSessions());
                    }
                }

                if (activeId) {
                    const res = await sendChatMessageApi(activeId, text);
                    if (res && res.assistant_message) {
                        dispatch({
                            type: actionTypes.ADD_ASSISTANT_MESSAGE,
                            userMessage: res.user_message,
                            assistantMessage: res.assistant_message
                        });
                    }
                }
            }
        } catch (e) {
            ToastUtil.error(e.friendlyMessage || 'Lỗi khi nhận câu trả lời từ RAG AI.');
        } finally {
            dispatch({ type: actionTypes.SET_IS_SENDING_MESSAGE, isSending: false });
        }
    };
};

