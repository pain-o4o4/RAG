import { combineReducers } from 'redux';
import { persistReducer } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import autoMergeLevel2 from 'redux-persist/lib/stateReconciler/autoMergeLevel2';

import appReducer from './appReducer';
import userReducer from './userReducer';
import ragReducer from './ragReducer';

const persistCommonConfig = {
    storage: storage,
    stateReconciler: autoMergeLevel2
};

const appPersistConfig = {
    ...persistCommonConfig,
    key: 'app',
    whitelist: ['activeTab', 'isSidebarOpen']
};

const userPersistConfig = {
    ...persistCommonConfig,
    key: 'user',
    whitelist: ['isLoggedIn', 'userInfo']
};

const rootReducer = combineReducers({
    app: persistReducer(appPersistConfig, appReducer),
    user: persistReducer(userPersistConfig, userReducer),
    rag: ragReducer
});

export default rootReducer;
