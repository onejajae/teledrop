<script>
	import { Listgroup, ListgroupItem, Heading } from 'flowbite-svelte';
	import { getUploadList } from '$api/upload';
</script>

<Heading tag="h3" class="mb-4">내 업로드</Heading>
<Listgroup active>
	{#await getUploadList() then data}
		{#each data as upload}
			<ListgroupItem href="/{upload.key}">
				<div class="me-auto ms-2 py-1">
					<div class="truncate text-base font-semibold">{upload.filename}</div>
					<div class="text-sm font-light">{upload.datetime}</div>
				</div>
			</ListgroupItem>
		{/each}
	{/await}
</Listgroup>
