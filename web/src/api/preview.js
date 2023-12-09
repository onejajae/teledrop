import axiosInstance from '$utils/axiosInstance';
import { accessToken } from '$lib';
import { get } from 'svelte/store';

async function getFileInfo(key, password = null) {
	const params = {};
	const headers = {};

	const access_token = get(accessToken.access_token);
	if (access_token) headers.Authorization = `Bearer ${access_token}`;

	if (password !== null) params.password = password;

	const response = await axiosInstance.get(`/preview/${key}`, { params, headers });

	const url = new URL(response.data.url);
	if (password !== null) url.searchParams.append('password', password);
	if (access_token) url.searchParams.append('access_token', access_token);
	response.data.url = `//${url.toString()}`

	return response.data;
}

export { getFileInfo };
