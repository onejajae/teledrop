<script>
	import { Img, P } from 'flowbite-svelte';
	import { API } from '$lib/api.js';
	import { postPasswords, accessToken } from '$lib/store.js';

	export let post;

	const src = `${API.baseURL}/download/${post.key}?preview=true&${$accessToken ? `access_token=${$accessToken}` : ''}${$postPasswords[post.key] ? `&password=${$postPasswords[post.key]}` : ''}`;
</script>

{#if post.filetype.startsWith('image/')}
	<Img {src} />
{:else if post.filetype.startsWith('video/')}
	<video class="w-full" controls>
		<source src={`${src}#t=0.001`} type={post.filetype} />
		<track kind="captions" />
		이 브라우저에서는 미리보기가 지원되지 않습니다.
	</video>
{:else if post.filetype.startsWith('audio/')}
	<audio class="my-5 w-full px-2" controls>
		<source {src} type={post.filetype} />
	</audio>
{:else if post.filetype.startsWith('application/pdf')}
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
