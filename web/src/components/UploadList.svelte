<script>
	import { getUploadList } from '$api/upload';
</script>

<h2>내 업로드</h2>
<div class="list-group">
	{#await getUploadList() then data}
		{#each data as upload}
			<a
				href="/{upload.key}"
				class="list-group-item list-group-item-action d-flex justify-content-between align-items-start"
			>
				<div class="ms-2 me-auto">
					<div class="fw-semibold">{upload.filename}</div>
					<small class="fw-light">{upload.datetime}</small>
				</div>
				<!-- <span class="badge bg-primary rounded-pill">14</span> -->
			</a>
		{/each}
	{/await}
</div>
