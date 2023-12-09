import { get } from 'svelte/store';
import axiosInstance from '$utils/axiosInstance';
import { accessToken } from '$lib';

async function login(username, password) {
	const headers = {
		'Content-Type': 'application/x-www-form-urlencoded'
	};
	const params = {
		username,
		password
	};
	const response = await axiosInstance.post(`/auth/login/`, params, { headers });
	accessToken.access_token.set(response.data.access_token);
	accessToken.username.set(response.data.username);
}

async function refresh() {
	const headers = {
		Authorization: `Bearer ${get(accessToken.access_token)}`
	};
	const response = await axiosInstance.get(`/auth/refresh/`, { headers });
	accessToken.access_token.set(response.data.access_token);
	accessToken.username.set(response.data.username);

	return response.data;
}

async function logout() {
	accessToken.access_token.set('');
	accessToken.username.set('');
	location.reload();
}
export { login, refresh, logout };
