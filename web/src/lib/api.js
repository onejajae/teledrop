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
		const res = await instance.get(`/content/`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) }
		});
		postList.set(res.data.drops);

		return res.data;
	},

	async getUserInfo() {
		try {
			const res = await instance.get(`/auth/me`);
			isLogin.set(true);
			return res.data;
		} catch (error) {
			isLogin.set(false);
			throw error;
		}
	},

	async getKeyExist({ slug }) {
		const res = await instance.get(`/content/keycheck/${slug}`);
		return res.data;
	},

	async uploadPost({ formData }) {
		if (!Boolean(formData.get('slug'))) formData.delete('slug');

		uploadProgress.set(0);
		const res = await instance.post(`/content/`, formData, {
			onUploadProgress: (progressEvent) => {
				uploadProgress.update((percentage) =>
					Math.max(percentage, Math.round((progressEvent.loaded * 100) / progressEvent.total))
				);
			}
		});
		await this.getPostList();
		return res.data;
	},

	async deletePost({ slug, password }) {
		const res = await instance.delete(`/content/${slug}`, {
			params: { password }
		});

		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async updatePostDetail({ slug, password, formData }) {
		const res = await instance.patch(`/content/${slug}/detail`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostFavorite({ slug, password, is_favorite }) {
		const formData = new FormData();

		formData.set('favorite', is_favorite);

		const res = await instance.patch(`/content/${slug}/favorite`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostPermission({ slug, password, user_only }) {
		const formData = new FormData();

		formData.set('user_only', user_only);

		const res = await instance.patch(`/content/${slug}/permission`, formData);
		await this.getPostList();
		return res.data;
	},

	async updatePostPassword({ slug, formData }) {
		const res = await instance.patch(`/content/${slug}/password/set`, formData);
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async resetPostPassword({ slug, password }) {
		const res = await instance.patch(`/content/${slug}/password/remove`);
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async getPostPreview({ slug, password }) {
		const res = await instance.get(`/content/${slug}/preview`, {
			params: { password }
		});

		postPasswords.update((passwords) => {
			return { ...passwords, [slug]: password };
		});

		return res.data;
	}
};

export { API, API_BASE_URL };
