<script>
	import { DarkMode, A, Dropdown, P } from 'flowbite-svelte';
	import { LanguageOutline, GithubSolid } from 'flowbite-svelte-icons';
	import { API } from '$lib/api.js';
	import { accessToken } from '$lib/store.js';
	import Logo from './Logo.svelte';
</script>

<div class="flex justify-between">
	<div class="flex">
		{#if $accessToken}
			<A
				href="/"
				on:click={API.logout}
				class="mx-2 font-semibold hover:underline"
				color="dark:text-white text-gray-700">로그아웃</A
			>
		{/if}
	</div>
	<div class="flex">
		<!-- <A
			class="rounded-lg p-2.5 text-sm text-gray-500 hover:bg-gray-100 focus:outline-none dark:text-gray-400 dark:hover:bg-gray-700"
		>
			<LanguageOutline />
		</A>
		<Dropdown class=" space-y-1 p-2">
			<li class="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-600"><P>한국어</P></li>
			<li class="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-600"><P>English</P></li>
			<li class="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-600"><P>日本語</P></li>
		</Dropdown> -->
		<A
			href="//github.com/onejajae/teledrop"
			target="_blank"
			class="rounded-lg p-2.5 text-sm text-gray-500 hover:bg-gray-100 focus:outline-none dark:text-gray-400 dark:hover:bg-gray-700"
		>
			<GithubSolid />
		</A>
		<DarkMode />
	</div>
</div>
<div class="flex justify-center">
	<div class="m-3 w-full max-w-sm">
		<a href="/"><Logo></Logo></a>
	</div>
</div>
