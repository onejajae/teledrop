<script>
	import { API } from '$lib/api.js';
	import Section from '../Section.svelte';
	import Form from './Form.svelte';
	import Progress from './Progress.svelte';
	import Result from './Result.svelte';

	let waitUpload = true;
	let uploadResult;
	let file;

	async function handleUpload(event) {
		const formData = new FormData(event.target);
		formData.set('file', file);
		uploadResult = API.uploadDrop({ formData });
		waitUpload = false;
	}
</script>

{#if waitUpload}
	<Section>
		<span slot="title"> 파일 업로드 </span>
		<div slot="content">
			<Form {handleUpload} bind:file />
		</div>
	</Section>
{:else}
	{#await uploadResult}
		<Progress></Progress>
	{:then result}
		<Result {result} reload={() => (waitUpload = true)}></Result>
	{/await}
{/if}
