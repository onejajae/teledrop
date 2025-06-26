<script>
	import { Img, P } from 'flowbite-svelte';
	import { API_BASE_URL } from '$lib/api.js';
	import { dropPasswords } from '$lib/store.js';

	export let drop;

	const src = `${API_BASE_URL}/drop/${drop.slug}?preview=true${$dropPasswords[drop.slug] ? `&password=${$dropPasswords[drop.slug]}` : ''}`;
</script>

{#if drop.file_type.startsWith('image/')}
	<Img {src} />
{:else if drop.file_type.startsWith('video/')}
	<video class="w-full" controls>
		<source src={`${src}#t=0.001`} type={drop.file_type} />
		<track kind="captions" />
		이 브라우저에서는 미리보기가 지원되지 않습니다.
	</video>
{:else if drop.file_type.startsWith('audio/')}
	<audio class="my-5 w-full px-2" controls>
		<source {src} type={drop.file_type} />
	</audio>
{:else if drop.file_type.startsWith('application/pdf')}
	<object
		class="w-full"
		height="350vh"
		data={`${src}`}
		type="application/pdf"
		aria-label="preview-pdf"
	>
		<div class="flex h-full items-center">
			<div class=" w-full">
				<P class="text-center">PDF 미리보기가 지원되지 않습니다.</P>
			</div>
		</div>
	</object>
{:else}
	<div></div>
{/if}
