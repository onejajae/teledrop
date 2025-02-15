<script>
	import { DarkMode, A, Dropdown, P } from 'flowbite-svelte';
	import { LanguageOutline, GithubSolid } from 'flowbite-svelte-icons';
	import UserInfoModal from './UserInfoModal.svelte';
	import { API } from '$lib/api.js';
	import { isLogin } from '$lib/store.js';
	import Logo from './Logo.svelte';

	// let userInfoModal = false;
</script>

<div class="flex justify-between">
	<div class="flex">
		{#if $isLogin}
			<A
				on:click={API.logout}
				class="mx-2 font-semibold hover:underline"
				color="dark:text-white text-gray-700">로그아웃</A
			>
			<!-- <button on:click={() => (userInfoModal = true)} class="mx-2 hover:underline dark:text-white">
				<P class="font-semibold text-gray-700">내 정보</P>
			</button> -->
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
<!-- <UserInfoModal bind:open={userInfoModal} /> -->
