<script>
	import { DarkMode, A } from 'flowbite-svelte';
	import Logo from './Logo.svelte';
	import { logout } from '$api/auth';
	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
</script>

<div class="flex justify-between">
	{#if get(accessToken.access_token)}
		<A class="px-2 font-medium hover:underline" on:click={logout} color="dark dark:text-white"
			>로그아웃</A
		>
	{:else}
		<A class="px-2 font-medium hover:underline" href="/login" color="dark dark:text-white">로그인</A
		>
	{/if}
	<DarkMode />
</div>
<div class="flex justify-center">
	<div class="w-full max-w-sm p-3">
		<a href="/"><Logo></Logo></a>
	</div>
</div>
