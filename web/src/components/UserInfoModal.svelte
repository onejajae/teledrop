<script>
	import { Button, Modal, Label, Input, Textarea, Checkbox, Helper } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { API } from '$lib/api.js';

	export let open;

	let usePassword = false;
	let deletePassword = false;
	let password1;
	let password2;
	// onMount(async () => {
	// 	await API.getUserInfo();
	// });
</script>

<Modal title="내 정보" size="sm" bind:open outsideclose>fdsfsda</Modal>
