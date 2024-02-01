<script>
	import { Heading, Progressbar } from 'flowbite-svelte';
	import { sineOut } from 'svelte/easing';
	import { uploadProgress } from '$lib';
</script>

<div class="text-center">
	<Heading tag="h3">업로드 진행중...</Heading>
</div>
<Progressbar
	progress={$uploadProgress}
	size="h-4"
	labelInside
	animate
	precision={2}
	tweenDuration={1500}
	easing={sineOut}
	class="mt-6"
/>
