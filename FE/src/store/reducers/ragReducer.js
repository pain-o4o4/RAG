import actionTypes from '../actions/actionTypes';

const initialState = {
    documents: [],
    totalDocuments: 0,
    totalPages: 1,
    isLoadingDocuments: false,
    isUploading: false,
    sessions: [],
    activeSessionId: null,
    messages: [],
    isLoadingMessages: false,
    isSendingMessage: false
};

const ragReducer = (state = initialState, action) => {
    switch (action.type) {
        // Documents
        case actionTypes.FETCH_DOCUMENTS_START:
            return {
                ...state,
                isLoadingDocuments: true
            };
        case actionTypes.FETCH_DOCUMENTS_SUCCESS:
            return {
                ...state,
                documents: action.documents,
                totalDocuments: action.total,
                totalPages: action.totalPages,
                isLoadingDocuments: false
            };
        case actionTypes.FETCH_DOCUMENTS_FAILED:
            return {
                ...state,
                isLoadingDocuments: false
            };
        case actionTypes.UPLOAD_DOCUMENT_START:
            return {
                ...state,
                isUploading: true
            };
        case actionTypes.UPLOAD_DOCUMENT_SUCCESS:
        case actionTypes.UPLOAD_DOCUMENT_FAILED:
            return {
                ...state,
                isUploading: false
            };

        // Chat Sessions
        case actionTypes.FETCH_SESSIONS_SUCCESS:
            return {
                ...state,
                sessions: action.sessions
            };
        case actionTypes.SET_ACTIVE_SESSION:
            return {
                ...state,
                activeSessionId: action.sessionId
            };
        case actionTypes.DELETE_SESSION_SUCCESS:
            return {
                ...state,
                sessions: state.sessions.filter((s) => s.id !== action.sessionId),
                activeSessionId: state.activeSessionId === action.sessionId ? null : state.activeSessionId
            };

        // Chat Messages
        case actionTypes.FETCH_MESSAGES_START:
            return {
                ...state,
                isLoadingMessages: true
            };
        case actionTypes.FETCH_MESSAGES_SUCCESS:
            if (state.isSendingMessage && (!action.messages || action.messages.length === 0)) {
                return {
                    ...state,
                    isLoadingMessages: false
                };
            }
            return {
                ...state,
                messages: action.messages,
                isLoadingMessages: false
            };
        case actionTypes.ADD_USER_MESSAGE:
            return {
                ...state,
                messages: [...state.messages, action.message]
            };
        case actionTypes.ADD_ASSISTANT_MESSAGE: {
            const filtered = state.messages.filter((m) => !m.id?.startsWith?.('temp-'));
            const updated = action.userMessage ? [...filtered, action.userMessage] : state.messages;
            return {
                ...state,
                messages: [...updated, action.assistantMessage]
            };
        }
        case actionTypes.SET_IS_SENDING_MESSAGE:
            return {
                ...state,
                isSendingMessage: action.isSending
            };

        // Reset sessions & messages on logout
        case actionTypes.PROCESS_LOGOUT:
            return {
                ...initialState
            };

        default:
            return state;
    }
};

export default ragReducer;
