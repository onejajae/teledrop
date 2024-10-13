<script>
	import '../app.css';

	import Header from '../components/Header.svelte';
	import PostList from '../components/PostList.svelte';

	import { accessToken } from '$lib/store.js';
</script>

<svelte:head>
	<title>teledrop</title>
</svelte:head>
<div class="flex justify-center px-2">
	<div class="container max-w-screen-sm space-y-3">
		<header class="my-2">
			<Header></Header>
		</header>
		<main>
			{#key $accessToken}
				<slot />
			{/key}
		</main>
		{#if $accessToken}
			<PostList></PostList>
		{/if}
		<footer></footer>
	</div>
</div>
