import axios from 'axios';

import { get } from 'svelte/store';
import {
	accessToken,
	postList,
	uploadProgress,
	postPasswords,
	sortBy,
	orderBy
} from '$lib/store.js';

// const API_BASE_URL = import.meta.env.DEV ? `//${import.meta.env.VITE_API_HOST_DEVELOPMENT}/api` : `//${window.location.host}/api`;
const API_BASE_URL = "/api";
const instance = axios.create({ baseURL: API_BASE_URL });
const API = {
	async login({ formData }) {
		try {
			const res = await instance.post(`/auth/login`, formData, {
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
			});
			const token = res.data;
			accessToken.set(token.access_token);
		} catch (error) {
			accessToken.set('');
			throw error;
		}
	},

	async logout() {
		accessToken.set('');
	},

	async getPostList() {
		const res = await instance.get(`/content`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) },
			headers: {
				authorization: `Bearer ${get(accessToken)}`
			}
		});
		postList.set(res.data.contents);

		return res.data;
	},

	async getUserInfo() {
		try {
			const res = await instance.get(`/auth/me`, {
				headers: { authorization: `Bearer ${get(accessToken)}` }
			});
			return res.data;
		} catch (error) {
			await this.logout();
			throw error;
		}
	},

	async getKeyExist({ key }) {
		const res = await instance.get(`/content/keycheck/${key}`, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		return res.data;
	},

	async uploadPost({ formData }) {
		if (!Boolean(formData.get('key'))) formData.delete('key');

		uploadProgress.set(0);
		const res = await instance.post(`/content`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` },
			onUploadProgress: (progressEvent) => {
				uploadProgress.update((percentage) =>
					Math.max(percentage, Math.round((progressEvent.loaded * 100) / progressEvent.total))
				);
			}
		});
		await this.getPostList();
		return res.data;
	},

	async deletePost({ key, password }) {
		const res = await instance.delete(`/content/${key}`, {
			params: { password },
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});

		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	},

	async updatePostDetail({ key, password, formData }) {
		if (password) formData.set('password', password);
		const res = await instance.patch(`/content/${key}/detail`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	},

	async updatePostFavorite({ key, password, favorite }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('favorite', favorite);

		const res = await instance.patch(`/content/${key}/favorite`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	},

	async updatePostPermission({ key, password, user_only }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('user_only', user_only);

		const res = await instance.patch(`/content/${key}/permission`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	},

	async updatePostPassword({ key, formData }) {
		const res = await instance.patch(`/content/${key}/password`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	},

	async resetPostPassword({ key, password }) {
		const formData = new FormData();
		if (password) formData.set('password', password);
		const res = await instance.patch(`/content/${key}/reset`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	},

	async getPostPreview({ key, password }) {
		const res = await instance.get(`/content/${key}/preview`, {
			params: { password },
			headers: get(accessToken) ? { authorization: `Bearer ${get(accessToken)}` } : null
		});

		postPasswords.update((passwords) => {
			return { ...passwords, [key]: password };
		});

		return res.data;
	},
};

export { API, API_BASE_URL };