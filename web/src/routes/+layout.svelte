<script>
	import '../app.css';

	import Header from '../components/Header.svelte';
	import DropList from '../components/DropList.svelte';

	import { isLogin } from '$lib/store.js';
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
			{#key $isLogin}
				<slot />
			{/key}
		</main>
		{#if $isLogin}
			<DropList></DropList>
		{/if}
		<footer></footer>
	</div>
</div>
