import axios from 'axios';

let refreshTimer = null;
let store = null;

export const injectStoreForRefresh = (_store) => {
    store = _store;
};

const parseJwtExp = (token) => {
    try {
        const payloadBase64 = token.split('.')[1];
        const decoded = JSON.parse(atob(payloadBase64));
        return decoded.exp; // seconds
    } catch (e) {
        return null;
    }
};

export const startTimer = (token) => {
    stopTimer();
    if (!token) return;

    const exp = parseJwtExp(token);
    if (!exp) return;

    const expiresInMs = exp * 1000 - Date.now();
    // Schedule refresh 1 minute before expiration (or 10s if expiring very soon)
    const refreshDelayMs = Math.max(expiresInMs - 60 * 1000, 10 * 1000);

    refreshTimer = setTimeout(async () => {
        try {
            const res = await axios.post(
                `${process.env.REACT_APP_BACKEND_URL}/api/refresh-token`,
                {},
                { withCredentials: true }
            );

            if (res.data && res.data.errCode === 0 && res.data.newAccessToken) {
                const newToken = res.data.newAccessToken;
                localStorage.setItem('token', newToken);

                if (store) {
                    store.dispatch({
                        type: 'USER_LOGIN_SUCCESS',
                        userInfo: {
                            ...store.getState().user.userInfo,
                            token: newToken
                        }
                    });
                }
                startTimer(newToken);
            }
        } catch (error) {
            console.warn('[TokenRefreshManager] Silent refresh failed:', error.message);
        }
    }, refreshDelayMs);
};

export const stopTimer = () => {
    if (refreshTimer) {
        clearTimeout(refreshTimer);
        refreshTimer = null;
    }
};

export const restoreTimer = () => {
    const token = localStorage.getItem('token');
    if (token) {
        startTimer(token);
    }
};
