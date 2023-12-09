<script>
	export let file;

	function isDirectory() {
		if (!file[0].type) {
			alert('폴더를 업로드할 수 없습니다.');
			file = undefined;
		}
	}
</script>

<div class="mb-2">
	<input class="form-control" type="file" id="formFile" bind:files={file} on:change={isDirectory} />
</div>
