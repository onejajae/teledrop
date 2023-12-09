<script>
	import { filesize } from 'filesize';
	export let filename;
	export let url;
	export let fileSize;
</script>

<div class="">
	<div class="card">
		<div class="card-body">
			<div class="px-1">
				<h5 class="card-title mb-2">다운로드</h5>
				<p class="card-text text-truncate mb-0">{filename}</p>
				<small class="card-subtitle text-body-secondary"
					>{filesize(fileSize, { standard: 'jedec' })}</small
				>
			</div>
		</div>
		<a href={url} class="stretched-link"> </a>
	</div>
</div>

<style>
	.card:hover {
		transform: scale(1.01);
		border-color: rgba(var(--bs-dark-rgb));
	}
</style>
