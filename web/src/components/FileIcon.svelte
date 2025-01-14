<script>
	import {
		FileImageOutline,
		FileVideoOutline,
		FileMusicOutline,
		FileOutline,
		FilePdfOutline
	} from 'flowbite-svelte-icons';

	export let file_type;
	export let size = 'md';
	export let iconClass = '';
</script>

{#if file_type.startsWith('image/')}
	<FileImageOutline {size} class={iconClass} />
{:else if file_type.startsWith('video/')}
	<FileVideoOutline {size} class={iconClass} />
{:else if file_type.startsWith('audio/')}
	<FileMusicOutline {size} class={iconClass} />
{:else if file_type.startsWith('application/pdf')}
	<FilePdfOutline {size} class={iconClass} />
{:else}
	<FileOutline {size} class={iconClass} />
{/if}
