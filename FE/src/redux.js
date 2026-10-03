import { createStore, applyMiddleware, compose } from 'redux';
import thunkMiddleware from 'redux-thunk';
import { createStateSyncMiddleware } from 'redux-state-sync';
import { persistStore } from 'redux-persist';

import rootReducer from './store/reducers/rootReducer';
import actionTypes from './store/actions/actionTypes';

const reduxStateSyncConfig = {
    whitelist: [
        actionTypes.APP_START_UP_COMPLETE
    ]
};

const middleware = [
    thunkMiddleware,
    createStateSyncMiddleware(reduxStateSyncConfig),
];

const composeEnhancers =
    (process.env.NODE_ENV === 'development' && window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__)
        ? window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__
        : compose;

const reduxStore = createStore(
    rootReducer,
    composeEnhancers(applyMiddleware(...middleware))
);

export const dispatch = reduxStore.dispatch;
export const persistor = persistStore(reduxStore);

export default reduxStore;
