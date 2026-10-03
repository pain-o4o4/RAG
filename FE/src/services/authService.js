import axios from '../auth/axiosInstance';

export const handleLoginApi = (email, password) => {
    return axios.post('/api/v1/auth/login', { email, password });
};

export const handleRegisterApi = (user_name, email, password) => {
    return axios.post('/api/v1/auth/register', { user_name, email, password });
};

export const getHealthCheckApi = () => {
    return axios.get('/health');
};
