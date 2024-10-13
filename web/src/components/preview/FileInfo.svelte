<script>
	import { P } from 'flowbite-svelte';

	import FileIcon from '../FileIcon.svelte';

	import { filesize } from 'filesize';
	import dayjs from 'dayjs';
	import 'dayjs/locale/ko';
	dayjs.locale('ko');

	export let post;
</script>

<div class="flex items-center justify-center">
	<P><FileIcon filetype={post.filetype} iconClass="size-20" /></P>
	<div class="min-w-0 flex-col">
		<P size="md" class="truncate" weight="semibold">{post.filename}</P>
		<P size="sm">{filesize(post.filesize, { standard: 'jedec' })}</P>
		<P size="xs">{dayjs(post.created_at).format('YYYY-MM-DD (dd) HH:mm:ss')}</P>
	</div>
</div>
