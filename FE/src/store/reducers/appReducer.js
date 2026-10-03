import actionTypes from '../actions/actionTypes';

const initialState = {
    started: true,
    activeTab: 'chat', // 'chat' | 'documents' | 'system'
    isSidebarOpen: true,
    inspectorSource: null,
    backendHealth: {
        status: 'checking',
        service: 'RAG Backend API',
        docs: '/api/v1/docs'
    },
    contentOfConfirmModal: {
        isOpen: false,
        message: '',
        handleFunc: null,
        dataFunc: null
    }
};

const appReducer = (state = initialState, action) => {
    switch (action.type) {
        case actionTypes.APP_START_UP_COMPLETE:
            return {
                ...state,
                started: true
            };
        case actionTypes.SET_ACTIVE_TAB:
            return {
                ...state,
                activeTab: action.tab
            };
        case actionTypes.TOGGLE_SIDEBAR:
            return {
                ...state,
                isSidebarOpen: !state.isSidebarOpen
            };
        case actionTypes.SET_INSPECTOR_SOURCE:
            return {
                ...state,
                inspectorSource: action.source
            };
        case actionTypes.SET_BACKEND_HEALTH:
            return {
                ...state,
                backendHealth: action.health
            };
        case actionTypes.SET_CONTENT_OF_CONFIRM_MODAL:
            return {
                ...state,
                contentOfConfirmModal: action.contentOfConfirmModal
            };
        default:
            return state;
    }
};

export default appReducer;
