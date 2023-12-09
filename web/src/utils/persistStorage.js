import { writable } from 'svelte/store';

const localStorageWrapper = (key, initValue) => {
	const storedValueStr = localStorage.getItem(key);
	const store = writable(storedValueStr != null ? storedValueStr : initValue);
	store.subscribe((val) => {
		localStorage.setItem(key, val);
	});
	return store;
};

const sessionStorageWrapper = (key, initValue) => {
	const storedValueStr = sessionStorage.getItem(key);
	const store = writable(storedValueStr != null ? storedValueStr : initValue);
	store.subscribe((val) => {
		sessionStorage.setItem(key, val);
	});
	return store;
};

export {localStorageWrapper, sessionStorageWrapper}
