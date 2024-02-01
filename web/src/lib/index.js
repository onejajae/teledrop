// place files you want to import through the `$lib` alias in this folder.

import { writable } from 'svelte/store';
import { localStorageWrapper, sessionStorageWrapper } from '$utils/persistStorage';
const uploadProgress = writable(0);
const accessToken = {
	access_token: sessionStorageWrapper('access_token', ''),
	username: sessionStorageWrapper('username', '')
};

export { uploadProgress, accessToken };
