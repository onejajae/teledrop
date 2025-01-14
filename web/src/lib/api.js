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

export class API {
	static baseURL = `//${import.meta.env.VITE_API_HOST}${import.meta.env.VITE_API_BASE}`;
	static instance = axios.create({ baseURL: this.baseURL });

	static async login({ formData }) {
		try {
			const res = await this.instance.post(`/auth/login`, formData, {
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
			});
			const token = res.data;
			accessToken.set(token.access_token);
		} catch (error) {
			accessToken.set('');
			throw error;
		}
	}

	static async logout() {
		accessToken.set('');
	}

	static async getPostList() {
		const res = await this.instance.get(`/content`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) },
			headers: {
				authorization: `Bearer ${get(accessToken)}`
			}
		});
		postList.set(res.data.contents);

		return res.data;
	}

	static async getUserInfo() {
		try {
			const res = await this.instance.get(`/auth/me`, {
				headers: { authorization: `Bearer ${get(accessToken)}` }
			});
			return res.data;
		} catch (error) {
			await this.logout();
			throw error;
		}
	}

	static async getKeyExist({ key }) {
		const res = await this.instance.get(`/content/keycheck/${key}`, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		return res.data;
	}

	static async uploadPost({ formData }) {
		if (!Boolean(formData.get('key'))) formData.delete('key');

		uploadProgress.set(0);
		const res = await this.instance.post(`/content`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` },
			onUploadProgress: (progressEvent) => {
				uploadProgress.update((percentage) =>
					Math.max(percentage, Math.round((progressEvent.loaded * 100) / progressEvent.total))
				);
			}
		});
		await this.getPostList();
		return res.data;
	}

	static async deletePost({ key, password }) {
		const res = await this.instance.delete(`/content/${key}`, {
			params: { password },
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});

		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	}

	static async updatePostDetail({ key, password, formData }) {
		if (password) formData.set('password', password);
		const res = await this.instance.patch(`/content/${key}/detail`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	}

	static async updatePostFavorite({ key, password, favorite }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('favorite', favorite);

		const res = await this.instance.patch(`/content/${key}/favorite`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	}

	static async updatePostPermission({ key, password, user_only }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('user_only', user_only);

		const res = await this.instance.patch(`/content/${key}/permission`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	}

	static async updatePostPassword({ key, formData }) {
		const res = await this.instance.patch(`/content/${key}/password`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	}

	static async resetPostPassword({ key, password }) {
		const formData = new FormData();
		if (password) formData.set('password', password);
		const res = await this.instance.patch(`/content/${key}/reset`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		return res.data;
	}

	static async getPostPreview({ key, password }) {
		const res = await this.instance.get(`/content/${key}/preview`, {
			params: { password },
			headers: get(accessToken) ? { authorization: `Bearer ${get(accessToken)}` } : null
		});

		postPasswords.update((passwords) => {
			return { ...passwords, [key]: password };
		});

		return res.data;
	}
}
