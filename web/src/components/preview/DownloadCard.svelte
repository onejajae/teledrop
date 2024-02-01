<script>
	import { Card, Heading, P } from 'flowbite-svelte';
	import { filesize } from 'filesize';
	export let filename;
	export let url;
	export let fileSize;
</script>

<Card href={url} padding="md" size="xl">
	<Heading tag="h5">다운로드</Heading>
	<P size="base">{filename}</P>
	<P size="sm">{filesize(fileSize, { standard: 'jedec' })}</P>
</Card>
