<script>
	import { page } from '$app/stores';

	import { getFileInfo } from '$api/preview';

	import Loading from '$components/common/Loading.svelte';
	import Viewer from '$components/preview/viewer/Viewer.svelte';
	import Detail from '$components/preview/Detail.svelte';
	import DownloadCard from '$components/preview/DownloadCard.svelte';
	import Forbidden403 from '$components/preview/error/Forbidden403.svelte';
	import NotFound404 from '$components/preview/error/NotFound404.svelte';

	let key;
	let password;
	let isPasswordCorrect;
	let promise;
	if (password) isPasswordCorrect = false;
	else isPasswordCorrect = true;

	$: {
		if (key != $page.params.key) {
			key = $page.params.key;
			password = $page.url.searchParams.get('password');
			promise = getFileInfo(key, password);
		}
	}
</script>

{#await promise}
	<Loading></Loading>
{:then data}
	<div class="text-center">
		<Viewer {data}></Viewer>
	</div>
	<div class="d-flex justify-content-center mt-3">
		<div class="w-100">
			<Detail {data}></Detail>
			<DownloadCard filename={data.filename} url={data.url} fileSize={data.file_size}
			></DownloadCard>
		</div>
	</div>
{:catch error}
	{#if error.response.status === 403}
		<Forbidden403 bind:password bind:isPasswordCorrect {key} bind:promise></Forbidden403>
	{:else if error.response.status === 404}
		<NotFound404></NotFound404>
	{:else if error.response.status === 401}
		권한 없음
	{/if}
{/await}
