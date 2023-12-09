<script>
	import { uploadFile } from '$api/upload';
	import { refresh } from '$api/auth';
	import UploadResult from '$components/upload/UploadResult.svelte';
	import UploadStatus from '$components/upload/UploadStatus.svelte';
	import DetailInput from '$components/upload/DetailInput.svelte';
	import FileInput from '$components/upload/FileInput.svelte';
	import ErrorHandler from '$components/upload/error/ErrorHandler.svelte';
	import UploadButton from '$components/upload/UploadButton.svelte';
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
		console.log(uploadDetail);
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

{#await refresh()}
	<Loading></Loading>
{:then}
	{#if waitUpload}
		<h2>파일 업로드</h2>
		<FileInput bind:file></FileInput>
		<DetailInput bind:uploadDetail bind:isKeyDuplicated bind:isPasswordValid bind:isLogin
		></DetailInput>
		<UploadButton {upload} uploadAvailable={Boolean(file) && !isKeyDuplicated && isPasswordValid}
		></UploadButton>
	{:else}
		{#await uploadResult}
			<UploadStatus></UploadStatus>
		{:then data}
			<UploadResult uploadResult={data}></UploadResult>
			<div>
				<a href="/" on:click={reload}>업로드 화면으로 돌아가기</a>
			</div>
		{:catch error}
			<ErrorHandler {error}></ErrorHandler>
			<div>
				<a href="/" on:click={reload}>업로드 화면으로 돌아가기</a>
			</div>
		{/await}
	{/if}
{:catch}
	<Loading></Loading>
	<script>
		location.replace('/login');
	</script>
{/await}
