// place files you want to import through the `$lib` alias in this folder.

import { writable } from 'svelte/store';
import {localStorageWrapper, sessionStorageWrapper} from '$utils/persistStorage';
const uploadProgress = writable(0);
const accessToken = {
	access_token: localStorageWrapper('access_token', ''),
	username: localStorageWrapper('username', '')
};

export { uploadProgress, accessToken };
