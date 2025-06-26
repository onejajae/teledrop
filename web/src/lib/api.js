import axios from 'axios';

import { get } from 'svelte/store';
import { isLogin, dropList, uploadProgress, dropPasswords, sortBy, orderBy } from '$lib/store.js';

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
			dropPasswords.set({});
		} catch (error) {
			isLogin.set(false);
		}
	},

	async getDropList() {
		const res = await instance.get(`/drop/`, {
			params: { sortby: get(sortBy), orderby: get(orderBy) }
		});
		dropList.set(res.data.drops);

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

	async getSlugExists({ slug }) {
		const res = await instance.get(`/drop/${slug}/exists`);
		return res.data.exists;
	},

	async uploadDrop({ formData }) {
		if (!Boolean(formData.get('slug'))) formData.delete('slug');

		uploadProgress.set(0);
		const res = await instance.post(`/drop/`, formData, {
			onUploadProgress: (progressEvent) => {
				uploadProgress.update((percentage) =>
					Math.max(percentage, Math.round((progressEvent.loaded * 100) / progressEvent.total))
				);
			}
		});
		await this.getDropList();
		return res.data;
	},

	async deleteDrop({ slug, password }) {
		const res = await instance.delete(`/drop/${slug}`, {
			params: { password }
		});

		await this.getDropList();
		dropPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async updateDropDetail({ slug, password, formData }) {
		const res = await instance.patch(`/drop/${slug}/detail`, formData, {
			params: { password }
		});
		await this.getDropList();
		return res.data;
	},

	async updateDropFavorite({ slug, password, is_favorite }) {
		const formData = new FormData();

		formData.set('is_favorite', is_favorite);

		const res = await instance.patch(`/drop/${slug}/favorite`, formData, {
			params: { password }
		});
		await this.getDropList();
		return res.data;
	},

	async updateDropPermission({ slug, password, is_private }) {
		const formData = new FormData();

		formData.set('is_private', is_private);

		const res = await instance.patch(`/drop/${slug}/permission`, formData, {
			params: { password }
		});
		await this.getDropList();
		return res.data;
	},

	async updateDropPassword({ slug, formData }) {
		const res = await instance.patch(`/drop/${slug}/password/set`, formData);
		await this.getDropList();
		dropPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async resetDropPassword({ slug, password }) {
		const res = await instance.patch(`/drop/${slug}/password/remove`, null, {
			params: { password }
		});
		await this.getDropList();
		dropPasswords.update((passwords) => {
			delete passwords[slug];
			return passwords;
		});
		return res.data;
	},

	async getDropPreview({ slug, password }) {
		const res = await instance.get(`/drop/${slug}/preview`, {
			params: { password }
		});

		dropPasswords.update((passwords) => {
			return { ...passwords, [slug]: password };
		});

		return res.data;
	}
};

export { API, API_BASE_URL };
