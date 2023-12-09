<script>
	export let data;
</script>

{#if data.title !== data.filename}
	<h3>{data.title}</h3>
{/if}
{#if data.description}
	<div class="mt-2">
		<p style="white-space: pre-line;">{data.description}</p>
	</div>
{/if}
