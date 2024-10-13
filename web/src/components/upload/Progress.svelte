<script>
	import { Heading, Progressbar } from 'flowbite-svelte';
	import Section from '../Section.svelte';

	import { uploadProgress } from '$lib/store.js';
	import { sineOut } from 'svelte/easing';
</script>

<Section>
	<div slot="content">
		<div class="text-center">
			<Heading tag="h3">업로드 중...</Heading>
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
	</div>
</Section>
