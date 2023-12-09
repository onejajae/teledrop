import axiosInstance from '../utils/axiosInstance';
import { uploadProgress, accessToken } from '$lib';
import { get } from 'svelte/store';

async function uploadFile(file, detail) {
	const headers = {
		'Content-Type': 'multipart/form-data'
	};
	const access_token = get(accessToken.access_token);
	if (accessToken) {
		headers.Authorization = `Bearer ${access_token}`;
	}

	const formData = new FormData();

	if (detail.key) formData.append('key', detail.key);
	if (detail.title) formData.append('title', detail.title);
	if (detail.description) formData.append('description', detail.description);
	if (detail.password) formData.append('password', detail.password);

	formData.append('is_anonymous', detail.is_anonymous);
	formData.append('user_only', detail.user_only);
	formData.append('file', file[0]);

	const response = await axiosInstance.post('/upload/', formData, {
		headers: headers,
		onUploadProgress: (progressEvent) => {
			const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
			uploadProgress.set(percentage);
		}
	});
	return response.data;
}

async function isKeyExist(key) {
	const headers = {};

	const access_token = get(accessToken.access_token);
	if (access_token) headers.Authorization = `Bearer ${access_token}`;

	const response = await axiosInstance.get(`/keycheck/`, { params: { key }, headers });
	return response.data;
}

async function getUploadList() {
	const headers = {
		Authorization: `Bearer ${get(accessToken.access_token)}`
	};
	const params = {};
	const response = await axiosInstance.post(`/list/`, params, { headers });
	return response.data;
}

export { uploadFile, isKeyExist, getUploadList };
