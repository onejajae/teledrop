<script>
	import '../app.pcss';

	import Header from '$components/Header.svelte';
	import Footer from '$components/Footer.svelte';
	import UploadList from '$components/UploadList.svelte';

	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
</script>

<div class="flex justify-center px-2">
	<div class="container max-w-screen-sm">
		<header class="my-2">
			<Header></Header>
		</header>
		<main class="my-5 rounded-xl bg-gray-50 p-5 shadow-xl dark:bg-gray-700">
			<slot />
		</main>
		{#if get(accessToken.access_token)}
			<div class="my-5 rounded-xl bg-gray-50 p-5 shadow-xl dark:bg-gray-700">
				<UploadList></UploadList>
			</div>
		{/if}
		<footer>
			<Footer></Footer>
		</footer>
	</div>
</div>
