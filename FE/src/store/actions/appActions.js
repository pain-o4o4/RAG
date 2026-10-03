import actionTypes from './actionTypes';
import { getHealthCheckApi } from '../../services/userService';

export const appStartUpComplete = () => ({
    type: actionTypes.APP_START_UP_COMPLETE
});

export const setActiveTab = (tab) => ({
    type: actionTypes.SET_ACTIVE_TAB,
    tab
});

export const toggleSidebar = () => ({
    type: actionTypes.TOGGLE_SIDEBAR
});

export const setInspectorSource = (source) => ({
    type: actionTypes.SET_INSPECTOR_SOURCE,
    source
});

export const setContentOfConfirmModal = (contentOfConfirmModal) => ({
    type: actionTypes.SET_CONTENT_OF_CONFIRM_MODAL,
    contentOfConfirmModal
});

export const checkBackendHealth = () => {
    return async (dispatch) => {
        try {
            const res = await getHealthCheckApi();
            dispatch({
                type: actionTypes.SET_BACKEND_HEALTH,
                health: res
            });
        } catch (e) {
            dispatch({
                type: actionTypes.SET_BACKEND_HEALTH,
                health: {
                    status: 'offline',
                    service: 'RAG Backend API (Offline)',
                    error: e.friendlyMessage || e.message
                }
            });
        }
    };
};
