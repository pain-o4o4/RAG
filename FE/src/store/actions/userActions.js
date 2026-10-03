import actionTypes from './actionTypes';
import { handleLoginApi, handleRegisterApi } from '../../services/userService';
import { ToastUtil } from '../../utils/ToastUtil';

export const userLoginSuccess = (userInfo) => ({
    type: actionTypes.USER_LOGIN_SUCCESS,
    userInfo: userInfo
});

export const userLoginFail = () => ({
    type: actionTypes.USER_LOGIN_FAIL
});

export const processLogout = () => ({
    type: actionTypes.PROCESS_LOGOUT
});

export const loginUserThunk = (email, password, onSuccess) => {
    return async (dispatch) => {
        try {
            const data = await handleLoginApi(email, password);
            if (data && data.user) {
                dispatch(userLoginSuccess(data.user));
                ToastUtil.success(data.message || 'Đăng nhập thành công!');
                if (onSuccess) onSuccess(data.user);
            } else {
                ToastUtil.error('Đăng nhập không thành công');
            }
        } catch (err) {
            const msg = err.friendlyMessage || 'Đăng nhập thất bại!';
            ToastUtil.error(msg);
        }
    };
};

export const registerUserThunk = (user_name, email, password, onSuccess) => {
    return async (dispatch) => {
        try {
            const data = await handleRegisterApi(user_name, email, password);
            if (data && data.id) {
                dispatch({ type: actionTypes.USER_REGISTER_SUCCESS });
                ToastUtil.success('Đăng ký tài khoản thành công! Vui lòng đăng nhập.');
                if (onSuccess) onSuccess();
            } else {
                ToastUtil.error('Đăng ký không thành công');
            }
        } catch (err) {
            const msg = err.friendlyMessage || 'Đăng ký thất bại!';
            ToastUtil.error(msg);
        }
    };
};
