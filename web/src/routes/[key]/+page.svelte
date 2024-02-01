<script>
	import { Button } from 'flowbite-svelte';

	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
	import { goto } from '$app/navigation';

	import { getFileInfo, deleteFile } from '$api/preview';

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

	async function deleteHandle() {
		if (confirm('정말 삭제하시겠습니까?')) {
			await deleteFile(key, password);
			alert('삭제가 완료되었습니다.');
			goto('/');
		}
	}

	$: {
		if (key != $page.params.key) {
			key = $page.params.key;
			password = $page.url.searchParams.get('password');
			promise = getFileInfo(key, password);
		}
	}
</script>

<svelte:head>
	<title>teledrop</title>
</svelte:head>
{#await promise}
	<Loading></Loading>
{:then data}
	<div class="flex justify-center">
		<Viewer {data}></Viewer>
	</div>
	<div class="w-100 my-5">
		<Detail {data}></Detail>
		<DownloadCard filename={data.filename} url={data.url} fileSize={data.file_size}></DownloadCard>
	</div>

	{#if data.username === get(accessToken.username)}
		<div class="text-end">
			<Button color="red" outline on:click={deleteHandle}>삭제</Button>
		</div>
	{/if}
{:catch error}
	{#if error.response.status === 403}
		<Forbidden403 bind:password bind:isPasswordCorrect {key} bind:promise></Forbidden403>
	{:else if error.response.status === 404}
		<NotFound404></NotFound404>
	{:else if error.response.status === 401}
		권한 없음
	{/if}
{/await}
