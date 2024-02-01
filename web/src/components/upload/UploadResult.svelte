<script>
	import { Heading, A } from 'flowbite-svelte';
	import { page } from '$app/stores';
	import { uploadProgress } from '$lib';
	export let uploadResult;

	uploadProgress.set(0);
</script>

<div class="text-center">
	<Heading tag="h3">업로드 완료</Heading>
</div>
<div class="mt-3">
	<dl>
		<dt class="mb-2 font-semibold leading-none text-gray-900 dark:text-white">파일명</dt>
		<dd class="mb-4 font-light text-gray-500 dark:text-gray-400 sm:mb-5">
			{uploadResult.filename}
		</dd>
	</dl>
	{#if uploadResult.title !== uploadResult.filename}
		<dl>
			<dt class="mb-2 font-semibold leading-none text-gray-900 dark:text-white">제목</dt>
			<dd class="mb-4 font-light text-gray-500 dark:text-gray-400 sm:mb-5">{uploadResult.title}</dd>
		</dl>
	{/if}
	{#if uploadResult.description}
		<dl>
			<dt class="mb-2 font-semibold leading-none text-gray-900 dark:text-white">설명</dt>
			<dd class="mb-4 font-light text-gray-500 dark:text-gray-400 sm:mb-5">
				{uploadResult.description}
			</dd>
		</dl>
	{/if}
	<dl>
		<dt class="mb-2 font-semibold leading-none text-gray-900 dark:text-white">업로드 시간</dt>
		<dd class="mb-4 font-light text-gray-500 dark:text-gray-400 sm:mb-5">
			{uploadResult.datetime}
		</dd>
	</dl>
	<dl>
		<dt class="mb-2 font-semibold leading-none text-gray-900 dark:text-white">바로가기 링크</dt>
		<dd class="mb-4 font-light text-gray-500 dark:text-gray-400 sm:mb-5">
			<A href="/{uploadResult.key}">{$page.url}{uploadResult.key}</A>
		</dd>
	</dl>
</div>
