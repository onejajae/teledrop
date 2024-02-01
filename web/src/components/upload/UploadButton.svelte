<script>
	import { Button } from 'flowbite-svelte';
	export let upload;
	export let uploadAvailable;
</script>

<div class="text-center">
	<button
		type="button"
		class="w-50 btn btn-success mt-2"
		class:shake={uploadAvailable}
		on:click={upload}
		class:disabled={!uploadAvailable}>업로드</button
	>
</div>
<Button color="green" outline pill disabled={!uploadAvailable} on:click={upload}>업로드</Button>
