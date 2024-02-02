<script>
	import { Button, P } from 'flowbite-svelte';
	import dayjs from 'dayjs';
	import 'dayjs/locale/ko';
	dayjs.locale('ko');

	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import { accessToken } from '$lib';
	import { goto } from '$app/navigation';

	import { getFileInfo, deleteFile } from '$api/preview';
	import { refresh } from '$api/auth';

	import Loading from '$components/common/Loading.svelte';
	import Viewer from '$components/preview/viewer/Viewer.svelte';
	import Detail from '$components/preview/Detail.svelte';
	import DownloadCard from '$components/preview/DownloadCard.svelte';
	import Forbidden403 from '$components/preview/error/Forbidden403.svelte';
	import NotFound404 from '$components/preview/error/NotFound404.svelte';
	import Unauthorized401 from '$components/preview/error/Unauthorized401.svelte';

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
			refresh();
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

	<div class="flex justify-between">
		<P class="mt-3 ps-1">{dayjs(data.datetime).format('YYYY-MM-DD (dd) HH:mm:ss')} 등록</P>
		{#if data.username === get(accessToken.username)}
			<Button color="red" outline on:click={deleteHandle}>삭제</Button>
		{/if}
	</div>
{:catch error}
	{#if error.response.status === 403}
		<Forbidden403 bind:password bind:isPasswordCorrect {key} bind:promise></Forbidden403>
	{:else if error.response.status === 404}
		<NotFound404></NotFound404>
	{:else if error.response.status === 401}
		<Unauthorized401></Unauthorized401>
	{/if}
{/await}
