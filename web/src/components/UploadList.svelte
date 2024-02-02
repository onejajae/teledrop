<script>
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import 'dayjs/locale/ko';
	dayjs.extend(relativeTime);
	dayjs.locale('ko');

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
					<div class="text-sm font-light">{dayjs(upload.datetime).fromNow()}</div>
				</div>
			</ListgroupItem>
		{/each}
	{/await}
</Listgroup>
