import { writable } from 'svelte/store';

const persist_storage = (key, initValue) => {
	const storedValueStr = localStorage.getItem(key);
	const store = writable(storedValueStr ? storedValueStr : initValue);
	store.subscribe((val) => {
		localStorage.setItem(key, val);
	});
	return store;
};

export const isLogin = persist_storage('login', false);
export const postList = writable([]);
export const uploadProgress = writable(0);
export const postPasswords = writable({});
export const sortBy = writable('created_time');
export const orderBy = writable('desc');
