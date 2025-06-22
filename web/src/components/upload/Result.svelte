<script>
	import { Heading, Button, Img } from 'flowbite-svelte';
	import Section from '../Section.svelte';

	export let result;
	export let reload;
</script>

<Section>
	<div slot="content" class="flex flex-col items-center text-center">
		<Heading class="mb-3" tag="h4">업로드가 완료되었습니다.</Heading>
		<!-- <div class="mb-3">
			<Heading tag="h6">공유 QR코드</Heading>
			<Img src="https://placehold.co/200x200"/>
		</div> -->
	</div>
	<div slot="footer" class="flex justify-center pb-3">
		<Button class="mx-3 px-5" href="/" size="sm" on:click={reload} outline pill>계속 업로드</Button>
		<Button class="mx-3 px-5" href={`/${result.slug}`} size="sm" outline pill>파일 미리보기</Button>
	</div>
</Section>
