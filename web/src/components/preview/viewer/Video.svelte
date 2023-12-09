<script>
	export let src;
	export let type;
</script>

<div>
	<video class="w-100" controls>
		<source {src} {type} />
		<track kind="captions" />
		이 브라우저에서는 미리보기가 지원되지 않습니다.
	</video>
</div>
