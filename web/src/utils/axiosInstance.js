import axios from 'axios';

const instance = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL
});

// instance.defaults.withCredentials = true;

instance.interceptors.request.use(
	(config) => {
		return config;
	},
	(error) => {
		return Promise.reject(error);
	}
);

axios.interceptors.response.use(
	(config) => {
		return config;
	},
	(error) => {
		return Promise.reject(error);
	}
);

export default instance;
