<script>
	import { Heading, Button, A } from 'flowbite-svelte';
	import { uploadFile } from '$api/upload';
	import { refresh } from '$api/auth';

	import UploadResult from '$components/upload/UploadResult.svelte';
	import UploadStatus from '$components/upload/UploadStatus.svelte';
	import DetailInput from '$components/upload/DetailInput.svelte';
	import FileDropzone from '$components/upload/FileDropzone.svelte';
	import ErrorHandler from '$components/upload/error/ErrorHandler.svelte';
	import Loading from '$components/common/Loading.svelte';

	// data to send
	let file = undefined;
	let uploadDetail = undefined;
	// data from server
	let uploadResult = undefined;
	// states of this page
	let waitUpload = true;
	let isKeyDuplicated = false;
	let isPasswordValid = true;
	let isLogin = false;

	async function upload() {
		if (!file) {
			alert('파일을 선택해 주세요');
			return;
		}
		if (isKeyDuplicated) return;

		if (!isPasswordValid) return;

		waitUpload = false;
		uploadResult = uploadFile(file, uploadDetail);
	}

	function reload() {
		file = undefined;
		uploadDetail = undefined;
		uploadResult = undefined;
		waitUpload = true;
		isKeyDuplicated = false;
		isPasswordValid = true;
	}
</script>

<svelte:head>
	<title>teledrop</title>
</svelte:head>
{#await refresh()}
	<Loading></Loading>
{:then}
	{#if waitUpload}
		<Heading tag="h3" class="mb-4">파일 업로드</Heading>
		<!-- <FileInput bind:file /> -->
		<FileDropzone bind:file />
		<DetailInput bind:uploadDetail bind:isKeyDuplicated bind:isPasswordValid bind:isLogin />
		<div class="text-center">
			<Button
				class="mt-3"
				color="green"
				outline
				pill
				disabled={!(Boolean(file) && !isKeyDuplicated && isPasswordValid)}
				on:click={upload}>업로드</Button
			>
		</div>
	{:else}
		{#await uploadResult}
			<UploadStatus></UploadStatus>
		{:then data}
			<UploadResult uploadResult={data}></UploadResult>
			<A href="/" on:click={reload}>업로드 화면으로 돌아가기</A>
		{:catch error}
			<ErrorHandler {error}></ErrorHandler>
			<A href="/" on:click={reload}>업로드 화면으로 돌아가기</A>
		{/await}
	{/if}
{:catch}
	<Loading></Loading>
	<script>
		location.replace('/login');
	</script>
{/await}
