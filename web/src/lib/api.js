import axios from 'axios';

import { get } from 'svelte/store';
import { isLogin, postList, uploadProgress, postPasswords, sortBy, orderBy } from '$lib/store.js';

const API_BASE_URL = '/api';
const instance = axios.create({ baseURL: API_BASE_URL });
const API = {
	async login({ formData }) {
		try {
			const res = await instance.post(`/auth/login`, formData, {
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
			});
			isLogin.set(true);
		} catch (error) {
			isLogin.set(false);
			throw error;
		}
	},

	async logout() {
		try {
			const res = await instance.get(`/auth/logout`);
			isLogin.set(false);
		} catch (error) {
			isLogin.set(false);
		}
	},

	async getPostList() {
		const res = await instance.get(`/content`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) }
		});
		postList.set(res.data.contents);

		return res.data;
	},

	async getUserInfo() {
		try {
			const res = await instance.get(`/auth/me`);
			return res.data;
		} catch (error) {
			isLogin.set(false);
			throw error;
		}
	},

	async getKeyExist({ key }) {
		const res = await instance.get(`/content/keycheck/${key}`);
		return res.data;
	},

	async uploadPost({ formData }) {
		if (!Boolean(formData.get('key'))) formData.delete('key');

		uploadProgress.set(0);
		const res = await instance.post(`/content`, formData, {
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
			params: { password }
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
		const res = await instance.patch(`/content/${key}/detail`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostFavorite({ key, password, favorite }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('favorite', favorite);

		const res = await instance.patch(`/content/${key}/favorite`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostPermission({ key, password, user_only }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('user_only', user_only);

		const res = await instance.patch(`/content/${key}/permission`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostPassword({ key, formData }) {
		const res = await instance.patch(`/content/${key}/password`, formData);
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
		const res = await instance.patch(`/content/${key}/reset`, formData);
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	},

	async getPostPreview({ key, password }) {
		const res = await instance.get(`/content/${key}/preview`, {
			params: { password }
		});

		postPasswords.update((passwords) => {
			return { ...passwords, [key]: password };
		});

		return res.data;
	}
};

export { API, API_BASE_URL };
