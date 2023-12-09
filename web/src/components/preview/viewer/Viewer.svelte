<script>
	import { isImage, isVideo, isPDF } from '$utils/checkFileType';
	import Image from './Image.svelte';
	import Video from './Video.svelte';
	import PDF from './PDF.svelte';
	export let data;
</script>

<div></div>
{#if isImage(data.content_type)}
	<Image src={data.url}></Image>
{/if}
{#if isVideo(data.content_type)}
	<Video src={data.url} type={data.content_type}></Video>
{/if}
{#if isPDF(data.content_type)}
	<PDF src={data.url}></PDF>
{/if}
