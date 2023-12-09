<script>
	import Logo from './Logo.svelte';
	import { logout } from '$api/auth';
	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
</script>

<div class="mb-1 pt-2">
	{#if get(accessToken.access_token)}
		<button
			type="button"
			class="btn btn-link link-dark link-offset-2 link-underline link-underline-opacity-0"
			on:click={logout}>로그아웃</button
		>
	{:else}
		<a
			href="/login"
			class="btn btn-link link-dark link-offset-2 link-underline link-underline-opacity-0">로그인</a
		>
	{/if}
</div>
<div class="d-flex justify-content-center">
	<div class="w-50 p-3">
		<a href="/"><Logo></Logo></a>
	</div>
</div>
