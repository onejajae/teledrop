<script>
	import { uploadProgress } from '$lib';
</script>

<div class="text-center">
	<h1>업로드 중...</h1>
</div>
<div
	class="progress"
	role="progressbar"
	aria-label="Basic example"
	aria-valuenow={$uploadProgress}
	aria-valuemin="0"
	aria-valuemax="100"
>
	<div
		class="progress-bar progress-bar-striped progress-bar-animated"
		style="width: {$uploadProgress}%"
	>
		{$uploadProgress}%
	</div>
</div>
