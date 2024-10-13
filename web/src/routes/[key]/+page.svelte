<script>
	import Preview from '../../components/preview/Preview.svelte';
	import { page } from '$app/stores';
</script>

{#key $page.params.key}
	<Preview key={$page.params.key} />
{/key}
