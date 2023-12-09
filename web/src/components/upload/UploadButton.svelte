<script>
	export let upload;
	export let uploadAvailable;
</script>

<div class="text-center">
	<button
		type="button"
		class="w-50 mt-2 btn btn-success"
		class:shake={uploadAvailable}
		on:click={upload}
		class:disabled={!uploadAvailable}>업로드</button
	>
</div>

<style>
</style>
