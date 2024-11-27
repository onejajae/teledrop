import axios from 'axios';

import { get } from 'svelte/store';
import {
	accessToken,
	username,
	postList,
	uploadProgress,
	postPasswords,
	sortBy,
	orderBy,
	numPosts,
	usedCapacity,
	maxCapacity
} from '$lib/store.js';

export class API {
	static baseURL = `//${import.meta.env.VITE_API_HOST}${import.meta.env.VITE_API_BASE}`;
	static instance = axios.create({ baseURL: this.baseURL });

	static async login({ formData }) {
		try {
			const res = await this.instance.post(`/login`, formData, {
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
			});
			const token = res.data;
			accessToken.set(token.access_token);
			username.set(token.username);
		} catch (error) {
			accessToken.set('');
			username.set('');
			throw error;
		}
	}

	static async logout() {
		accessToken.set('');
		username.set('');
	}

	static async getPostList() {
		const res = await this.instance.get(`/list`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) },
			headers: {
				authorization: `Bearer ${get(accessToken)}`
			}
		});
		postList.set(res.data.posts);
		// numPosts.set(res.data.num_posts);
		// usedCapacity.set(res.data.used_capacity);
		// maxCapacity.set(res.data.max_capacity);

		return res.data;
	}

	static async getUserInfo() {
		try {
			const res = await this.instance.get(`/me`, {
				headers: { authorization: `Bearer ${get(accessToken)}` }
			});
			username.set(res.data.username);
			return res.data;
		} catch (error) {
			await this.logout();
			throw error;
		}
	}

	static async getKeyExist({ key }) {
		const res = await this.instance.get(`/keycheck`, {
			params: { key },
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		return res.data;
	}

	static async uploadPost({ formData }) {
		if (!Boolean(formData.get('key'))) formData.delete('key');

		uploadProgress.set(0);
		const res = await this.instance.post(`/upload`, formData, {
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
		const res = await this.instance.delete(`/delete/${key}`, {
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

	static async updatePost({ key, password, formData }) {
		if (password) formData.set('password', password);
		const res = await this.instance.put(`/update/${key}`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		postPasswords.update((passwords) => {
			delete passwords[key];
			return passwords;
		});
		await this.getPostList();
		return res.data;
	}

	static async updatePostFavorite({ key, password, favorite }) {
		const formData = new FormData();

		if (password) formData.set('password', password);
		formData.set('favorite', favorite);

		const res = await this.instance.patch(`/update/${key}/favorite`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		await this.getPostList();
		return res.data;
	}

	static async resetPostPassword({ key, formData }) {
		const res = await this.instance.patch(`/update/${key}/password`, formData, {
			headers: { authorization: `Bearer ${get(accessToken)}` }
		});
		return res.data;
	}

	static async getPostPreview({ key, password }) {
		const res = await this.instance.get(`/preview/${key}`, {
			params: { password },
			headers: get(accessToken) ? { authorization: `Bearer ${get(accessToken)}` } : null
		});

		postPasswords.update((passwords) => {
			return { ...passwords, [key]: password };
		});

		return res.data;
	}
}
