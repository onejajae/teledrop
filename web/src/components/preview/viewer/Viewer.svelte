<script>
	import { isImage, isVideo, isPDF } from '$utils/checkFileType';
	import Image from './Image.svelte';
	import Video from './Video.svelte';
	export let data;
</script>

<div></div>
{#if isImage(data.content_type)}
	<Image src={data.url}></Image>
{/if}
{#if isVideo(data.content_type)}
	<Video src={data.url} type={data.content_type}></Video>
{/if}
