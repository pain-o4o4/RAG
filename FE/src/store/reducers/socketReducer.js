import actionTypes from '../actions/actionTypes';

const initialState = {
    isConnected: false
};

const socketReducer = (state = initialState, action) => {
    switch (action.type) {
        case actionTypes.SOCKET_CONNECT:
            return {
                ...state,
                isConnected: true
            };
        case actionTypes.SOCKET_DISCONNECT:
            return {
                ...state,
                isConnected: false
            };
        default:
            return state;
    }
};

export default socketReducer;
