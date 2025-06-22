<script>
	import Preview from '../../components/preview/Preview.svelte';
	import { page } from '$app/stores';
</script>

{#key $page.params.slug}
	<Preview slug={$page.params.slug} />
{/key}
