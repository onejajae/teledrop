<script>
	import { API } from '$lib/api.js';

	import Upload from '../components/upload/Upload.svelte';
	import Login from '../components/Login.svelte';

	// import { onMount } from 'svelte';
	// let userLoading;

	// onMount(async () => {
	// 	try {
	// 		userLoading = API.getUserInfo();
	// 	} catch (error) {
	// 		await API.logout();
	// 	}
	// });
</script>

{#await API.getUserInfo() then user}
	<Upload />
{:catch error}
	<Login></Login>
{/await}
