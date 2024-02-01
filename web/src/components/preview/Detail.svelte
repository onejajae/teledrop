<script>
	import { Heading, P } from 'flowbite-svelte';
	export let data;
</script>

{#if data.title !== data.filename}
	<Heading tag="h3">{data.title}</Heading>
{/if}
{#if data.description}
	<P class="my-3">{data.description}</P>
{/if}
