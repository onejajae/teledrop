<script>
	import '../app.scss';
	import * as bootstrap from 'bootstrap';

	import Header from '$components/Header.svelte';
	import Footer from '$components/Footer.svelte';
	import UploadList from '$components/UploadList.svelte';

	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
</script>

<header class="container">
	<Header></Header>
</header>
<section class="container">
	<div class="my-2 p-4 rounded-4 shadow-lg">
		<slot />
	</div>
	{#if get(accessToken.access_token)}
		<div class="mt-5 p-4 rounded-4 shadow-lg">
			<UploadList></UploadList>
		</div>
	{/if}
</section>
<footer class="container">
	<Footer></Footer>
</footer>
