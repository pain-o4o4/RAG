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
                sessions: state.sessions.filter((s) => s.id !== action.sessionId)
            };

        // Chat Messages
        case actionTypes.FETCH_MESSAGES_START:
            return {
                ...state,
                isLoadingMessages: true
            };
        case actionTypes.FETCH_MESSAGES_SUCCESS:
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
            // Replace temporary user message if needed and append assistant message
            const filtered = state.messages.filter((m) => !m.id.startsWith('temp-'));
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

        default:
            return state;
    }
};

export default ragReducer;
