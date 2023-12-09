<script>
	import { page } from '$app/stores';
	import { uploadProgress } from '$lib';
	export let uploadResult;

	uploadProgress.set(0);
</script>

<div class="text-center">
	<h1>업로드 완료</h1>
</div>
<dl class="row mt-3">
	<dt class="col-sm-4">파일명</dt>
	<dd class="col-sm-8">{uploadResult.filename}</dd>
	<hr />
	{#if uploadResult.title !== uploadResult.filename}
		<dt class="col-sm-4">제목</dt>
		<dd class="col-sm-8">{uploadResult.title}</dd>
		<hr />
	{/if}
	{#if uploadResult.description}
		<dt class="col-sm-4">설명</dt>
		<dd class="col-sm-8"><p style="white-space: pre-line;">{uploadResult.description}</p></dd>
		<hr />
	{/if}
	<dt class="col-sm-4">업로드 시간</dt>
	<dd class="col-sm-8">{uploadResult.datetime}</dd>
	<hr />
	<dt class="col-sm-4">바로가기 링크</dt>
	<dd class="col-sm-8"><a href="/{uploadResult.key}">{$page.url}{uploadResult.key}</a></dd>
</dl>
