<script>
	import {
		FileImageOutline,
		FileVideoOutline,
		FileMusicOutline,
		FileOutline,
		FilePdfOutline
	} from 'flowbite-svelte-icons';

	export let filetype;
	export let size = 'md';
	export let iconClass = '';
</script>

{#if filetype.startsWith('image/')}
	<FileImageOutline {size} class={iconClass} />
{:else if filetype.startsWith('video/')}
	<FileVideoOutline {size} class={iconClass} />
{:else if filetype.startsWith('audio/')}
	<FileMusicOutline {size} class={iconClass} />
{:else if filetype.startsWith('application/pdf')}
	<FilePdfOutline {size} class={iconClass} />
{:else}
	<FileOutline {size} class={iconClass} />
{/if}
