<script>
	import { P, Tooltip } from 'flowbite-svelte';
	import { InfoCircleOutline } from 'flowbite-svelte-icons';

	import FileIcon from '../FileIcon.svelte';

	import { filesize } from 'filesize';
	import dayjs from 'dayjs';
	import 'dayjs/locale/ko';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import utc from 'dayjs/plugin/utc';
	dayjs.extend(relativeTime);
	dayjs.extend(utc);
	dayjs.locale('ko');

	export let post;
</script>

<div class="flex items-center justify-center">
	<P><FileIcon file_type={post.file_type} iconClass="size-20" /></P>
	<div class="min-w-0 flex-col">
		<P size="lg" class="truncate" weight="semibold">{post.file_name}</P>
		<P size="base">
			<div class="flex items-center">
				<span class="me-1">{filesize(post.file_size, { standard: 'jedec' })} </span>
			</div>
		</P>

		<P size="sm">
			<div class="flex items-center">
				<span class="me-1">
					{dayjs.utc(post.created_at).local().format('YYYY-MM-DD (dd) HH:mm:ss')} 에 업로드</span
				>
				{#if post.updated_at}
					<span><InfoCircleOutline size="sm" /></span>
					<Tooltip type="light"
						>{dayjs.utc(post.updated_at).local().format('YYYY-MM-DD (dd) HH:mm:ss')} 에 수정됨</Tooltip
					>
				{/if}
			</div>
		</P>
	</div>
</div>
