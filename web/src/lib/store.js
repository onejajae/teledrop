import { writable } from 'svelte/store';

const persist_storage = (key, initValue) => {
	const storedValueStr = localStorage.getItem(key);
	const store = writable(storedValueStr ? storedValueStr : initValue);
	store.subscribe((val) => {
		localStorage.setItem(key, val);
	});
	return store;
};

export const accessToken = persist_storage('accessToken', null);
export const username = persist_storage('username', null);
export const postList = writable([]);
export const numPosts = writable(0);
export const usedCapacity = writable(0);
export const maxCapacity = writable(0);
export const uploadProgress = writable(0);
export const postPasswords = writable({});
export const sortBy = writable('created_at');
export const orderBy = writable('desc');
