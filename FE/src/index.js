import React from 'react';
import { createRoot } from 'react-dom/client';
import 'react-toastify/dist/ReactToastify.css';
import './styles/styles.scss';

import App from './containers/App';
import SocketProvider from './context/SocketContext';

import { Provider } from 'react-redux';
import reduxStore, { persistor } from './redux';
import { injectStore } from './auth/axiosInstance';
import { injectStoreForRefresh, restoreTimer } from './auth/TokenRefreshManager';

// Inject Redux store into Axios instance for interceptor state access
injectStore(reduxStore);

// Inject Redux store into TokenRefreshManager for silent refresh state updates
injectStoreForRefresh(reduxStore);

// Restore refresh timer if user has active session on page reload
restoreTimer();

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
    <Provider store={reduxStore}>
        <SocketProvider>
            <App persistor={persistor} />
        </SocketProvider>
    </Provider>
);
